import base64
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from django.core.cache import cache
from django.db.models import Sum, QuerySet, Avg
from scipy import stats
from sklearn.cluster import KMeans
from xgboost import XGBRegressor
from statsmodels.tsa.arima.model import ARIMA

from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass, Subject
from apps.finance.models import Invoice, Receipt, SalaryInvoice, StudentUniform
from apps.result.models import Result
from apps.staffs.models import Staff
from apps.students.models import Student
from expenditures.models import Expenditure, ExpenditureInvoice

logger = logging.getLogger(__name__)

############################################
# Helper Functions
############################################

def _fig_to_base64(fig: go.Figure) -> str:
    """Return a Plotly figure as a base64-encoded PNG."""
    buf = io.BytesIO(); fig.write_image(buf, format="png"); buf.seek(0)
    return base64.b64encode(buf.read()).decode()



def use_advanced_model_if_possible(x: np.ndarray, y: np.ndarray) -> Tuple[XGBRegressor, str]:
    """Use XGBoost for prediction with sufficient data points."""
    model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    model.fit(x, y.ravel())
    return model, "XGBoost"

def generate_comments_and_advice(
    overall_avg: float,
    latest_avg: float,
    strongest: List[str],
    medium: List[str],
    weakest: List[str],
    z_score: float,
    class_avg: float
) -> str:
    """
    Generate modernized comments and advice based on performance metrics, z-score, and class comparison.
    Note: Scores are on a 100-point scale.
    """
    advice = []

    # Compare with class average
    if overall_avg > class_avg + 10:
        advice.append(f"Performance is well above class average ({overall_avg:.2f} vs {class_avg:.2f}/100).")
    elif overall_avg < class_avg - 10:
        advice.append(f"Performance is below class average ({overall_avg:.2f} vs {class_avg:.2f}/100).")
    else:
        advice.append(f"Performance is near class average ({overall_avg:.2f} vs {class_avg:.2f}/100).")

    # Z-score based commentary
    if z_score > 1.5:
        advice.append("Exceptionally high performance (z-score: {:.2f}). Encourage leadership roles.".format(z_score))
    elif z_score < -1.5:
        advice.append("Significantly below expectation (z-score: {:.2f}). Urgent intervention recommended.".format(z_score))
    else:
        advice.append("Performance within expected range (z-score: {:.2f}).".format(z_score))

    # Trend analysis
    trend = "improving" if latest_avg > overall_avg else "declining" if latest_avg < overall_avg else "stable"
    advice.append(f"Recent trend: {trend} (latest: {latest_avg:.2f}/100, overall: {overall_avg:.2f}/100).")

    # Subject-level feedback with prioritization
    if weakest:
        advice.append(f"**High Priority**: Weakest subjects: {', '.join(weakest)}. Schedule tutoring and extra classes.")
    if medium:
        advice.append(f"**Medium Priority**: Moderate subjects: {', '.join(medium)}. Assign targeted homework and monitor progress.")
    if strongest:
        advice.append(f"**Low Priority**: Strongest subjects: {', '.join(strongest)}. Encourage peer teaching or advanced projects.")

    return " ".join(advice)

def detect_anomalies(data: np.ndarray) -> List[int]:
    """Detect anomalies using z-scores with a threshold of 2 standard deviations."""
    z_scores = np.abs(stats.zscore(data))
    return [i for i, z in enumerate(z_scores) if z > 2]

############################################
# Clustering Subjects by Performance
############################################

def cluster_subjects_by_performance() -> Tuple[Optional[str], Dict[str, int], Optional[str]]:
    """
    Use K-Means clustering to group subjects by performance, with interactive Plotly visualization.
    Returns a base64 chart, subject-to-cluster map, and error message if any.
    """
    cache_key = "subject_clusters"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        results = Result.objects.select_related('subject').all()
        if not results.exists():
            return None, {}, "No results data for clustering."

        subject_ids = results.values_list('subject', flat=True).distinct()
        subjects = Subject.objects.filter(pk__in=subject_ids)
        subject_averages = []

        for subj in subjects:
            subj_results = results.filter(subject=subj).exclude(average__isnull=True)
            if subj_results.exists():
                avg_score = float(subj_results.aggregate(avg=Avg('average'))['avg'])
                subject_averages.append((subj.name, avg_score))

        if len(subject_averages) < 3:
            return None, {}, "Not enough subjects to form clusters (minimum 3 required)."

        df = pd.DataFrame(subject_averages, columns=['Subject', 'AverageScore'])
        X = df[['AverageScore']].values

        kmeans = KMeans(n_clusters=3, random_state=42)
        kmeans.fit(X)
        df['Cluster'] = kmeans.labels_
        df['Cluster'] = df['Cluster'].map({0: 'Low', 1: 'Medium', 2: 'High'})

        fig = px.scatter(
            df,
            x='AverageScore',
            y=[0]*len(df),
            color='Cluster',
            text='Subject',
            title="Subject Clusters by Average Performance (Out of 100)",
            labels={'AverageScore': 'Average Score'},
            color_discrete_map={'Low': '#FF6347', 'Medium': '#FFD700', 'High': '#32CD32'}
        )
        fig.update_traces(textposition='top center', marker=dict(size=12))
        fig.update_layout(
            yaxis=dict(show=False, showticklabels=False),
            xaxis_title="Average Score (0-100)",
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=50)
        )

        chart_base64 = _figure_to_base64(fig)
        cluster_labels = dict(zip(df['Subject'], df['Cluster']))
        cache.set(cache_key, (chart_base64, cluster_labels, None), timeout=3600)  # Cache for 1 hour
        return chart_base64, cluster_labels, None

    except Exception as e:
        logger.error(f"Error in cluster_subjects_by_performance: {str(e)}", exc_info=True)
        return None, {}, f"Error clustering subjects: {str(e)}"

############################################
# Class Performance Trends
############################################

def draw_class_performance_trends() -> Dict[str, Dict[str, Any]]:
    """
    Draw interactive class performance trends over sessions, terms, and exams using Plotly.
    All averages considered are out of 100.
    """
    cache_key = "class_performance_trends"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        classes = StudentClass.objects.prefetch_related('result_set').all()
        sessions = AcademicSession.objects.all()
        terms = AcademicTerm.objects.all()
        exams = ExamType.objects.all()

        class_insights: Dict[str, Dict[str, Any]] = {}

        for student_class in classes:
            results = Result.objects.filter(current_class=student_class).exclude(average__isnull=True)
            data = []
            class_avg = float(results.aggregate(avg=Avg('average'))['avg'] or 0)

            for session in sessions:
                for term in terms:
                    for exam in exams:
                        class_results = results.filter(session=session, term=term, exam=exam)
                        if not class_results.exists():
                            continue
                        student_overall_averages = []
                        distinct_students = class_results.values_list('student', flat=True).distinct()
                        for student_id in distinct_students:
                            student_res = class_results.filter(student_id=student_id)
                            if student_res.exists():
                                avg_per_student = float(student_res.aggregate(a=Avg('average'))['a'])
                                student_overall_averages.append(avg_per_student)

                        if student_overall_averages:
                            class_overall_avg = sum(student_overall_averages) / len(student_overall_averages)
                            data.append({
                                'Session': session.name,
                                'Term': term.name,
                                'Exam': exam.name,
                                'Overall Average': class_overall_avg
                            })

            if not data:
                class_insights[student_class.name] = {
                    'graph': None,
                    'latest_average': None,
                    'predicted_average': None,
                    'comments_and_advice': "No performance data available for this class."
                }
                continue

            df = pd.DataFrame(data)
            df['Overall Average'] = df['Overall Average'].astype(float)
            df['Index'] = range(len(df))
            latest_average = df['Overall Average'].iloc[-1]

            # Anomaly detection
            anomalies = detect_anomalies(df['Overall Average'].values)
            df['Anomaly'] = False
            for idx in anomalies:
                df.loc[idx, 'Anomaly'] = True

            x = df['Index'].values.reshape(-1, 1)
            y = df['Overall Average'].values.reshape(-1, 1)
            model, model_type = use_advanced_model_if_possible(x, y)
            predicted_average = float(model.predict([[len(df)]])[0])

            # Statistical analysis
            z_score = float(stats.zscore([latest_average], df['Overall Average'].values)[0])
            comments_and_advice = generate_comments_and_advice(
                df['Overall Average'].mean(), latest_average, [], [], [], z_score, class_avg
            )

            # Interactive Plotly chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam'],
                y=df['Overall Average'],
                name='Overall Average',
                marker_color='skyblue',
                opacity=0.7
            ))
            fig.add_trace(go.Scatter(
                x=df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam'],
                y=df['Overall Average'],
                mode='lines+markers',
                name='Trend Line',
                line=dict(color='orange', width=2),
                marker=dict(size=8)
            ))
            if anomalies:
                fig.add_trace(go.Scatter(
                    x=[(df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam']).iloc[i] for i in anomalies],
                    y=[df['Overall Average'].iloc[i] for i in anomalies],
                    mode='markers',
                    name='Anomalies',
                    marker=dict(color='red', size=12, symbol='x')
                ))

            fig.update_layout(
                title=f"Performance Trends: {student_class.name} (Model: {model_type})",
                xaxis_title="Session - Term - Exam",
                yaxis_title="Overall Average (Out of 100)",
                xaxis_tickangle=-45,
                title_font=dict(size=16, family="Poppins", color="#1B263B"),
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=50, b=50)
            )
            fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

            image_base64 = _figure_to_base64(fig)

            class_insights[student_class.name] = {
                'graph': image_base64,
                'latest_average': latest_average,
                'predicted_average': predicted_average,
                'comments_and_advice': comments_and_advice
            }

        cache.set(cache_key, class_insights, timeout=3600)  # Cache for 1 hour
        return class_insights

    except Exception as e:
        logger.error(f"Error in draw_class_performance_trends: {str(e)}", exc_info=True)
        return {}

############################################
# Student Trends in Classes
############################################

def draw_student_trends_in_classes() -> Dict[str, Dict[int, Dict[str, Any]]]:
    """
    Draws interactive performance trends for each student in their classes using Plotly.
    Using average (out of 100) from the Result model.
    """
    cache_key = "student_trends_in_classes"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        classes = StudentClass.objects.prefetch_related('result_set__student').all()
        sessions = AcademicSession.objects.all()
        terms = AcademicTerm.objects.all()
        exams = ExamType.objects.all()
        trends_data: Dict[str, Dict[int, Dict[str, Any]]] = {}

        for student_class in classes:
            results = Result.objects.filter(current_class=student_class).exclude(average__isnull=True)
            students = results.values_list('student', flat=True).distinct()
            class_avg = float(results.aggregate(avg=Avg('average'))['avg'] or 0)

            class_students_data: Dict[int, Dict[str, Any]] = {}
            for student_id in students:
                student_obj = Student.objects.filter(id=student_id).first()
                if not student_obj:
                    continue

                student_data = []
                subject_overall_averages: Dict[str, List[float]] = {}

                for session in sessions:
                    for term in terms:
                        for exam in exams:
                            student_results = results.filter(student=student_id, session=session, term=term, exam=exam)
                            if not student_results.exists():
                                continue
                            avg_scores = list(student_results.values_list('average', flat=True))
                            avg_scores = [float(v) for v in avg_scores if v is not None]
                            if avg_scores:
                                overall_average = sum(avg_scores) / len(avg_scores)
                                for r in student_results:
                                    subj_name = r.subject.name
                                    subject_overall_averages.setdefault(subj_name, []).append(float(r.average))
                                student_data.append({
                                    'Session': session.name,
                                    'Term': term.name,
                                    'Exam': exam.name,
                                    'Overall Average': overall_average,
                                })

                if not student_data:
                    continue

                df = pd.DataFrame(student_data)
                df['Session-Term-Exam'] = df['Session'] + " - " + df['Term'] + " - " + df['Exam']
                df['Overall Average'] = df['Overall Average'].astype(float)

                x = np.arange(len(df)).reshape(-1, 1)
                y = df['Overall Average'].values.reshape(-1, 1)

                if len(df) > 1:
                    model, _ = use_advanced_model_if_possible(x, y)
                    predicted_average = float(model.predict([[len(df)]])[0])
                else:
                    predicted_average = df['Overall Average'].iloc[-1]

                latest_average = df['Overall Average'].iloc[-1]
                overall_average = df['Overall Average'].mean()

                # Anomaly detection
                anomalies = detect_anomalies(df['Overall Average'].values)

                # Subject performance analysis
                strongest_subjects, medium_subjects, weakest_subjects = [], [], []
                for subj, avgs in subject_overall_averages.items():
                    avg = sum(avgs) / len(avgs)
                    if avg > 80:
                        strongest_subjects.append(subj)
                    elif 50 < avg <= 80:
                        medium_subjects.append(subj)
                    else:
                        weakest_subjects.append(subj)

                z_score = float(stats.zscore([latest_average], df['Overall Average'].values)[0])
                comments_and_advice = generate_comments_and_advice(
                    overall_average, latest_average, strongest_subjects, medium_subjects, weakest_subjects, z_score, class_avg
                )

                # Interactive Plotly chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['Session-Term-Exam'],
                    y=df['Overall Average'],
                    name='Overall Average',
                    marker_color='skyblue',
                    opacity=0.7
                ))
                fig.add_trace(go.Scatter(
                    x=df['Session-Term-Exam'],
                    y=df['Overall Average'],
                    mode='lines+markers',
                    name='Trend Line',
                    line=dict(color='orange', width=2),
                    marker=dict(size=8)
                ))
                if anomalies:
                    fig.add_trace(go.Scatter(
                        x=[df['Session-Term-Exam'].iloc[i] for i in anomalies],
                        y=[df['Overall Average'].iloc[i] for i in anomalies],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(color='red', size=12, symbol='x')
                    ))

                fig.update_layout(
                    title=f"Performance Trends for {student_obj.firstname} {student_obj.surname} in {student_class.name}",
                    xaxis_title="Session - Term - Exam",
                    yaxis_title="Overall Average (Out of 100)",
                    xaxis_tickangle=-45,
                    title_font=dict(size=16, family="Poppins", color="#1B263B"),
                    showlegend=True,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=50, b=50)
                )
                fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

                image_base64 = _figure_to_base64(fig)

                class_students_data[student_id] = {
                    'name': f"{student_obj.firstname} {student_obj.middle_name} {student_obj.surname}",
                    'graph': image_base64,
                    'latest_average': latest_average,
                    'over_and_over_average': overall_average,
                    'predicted_average': predicted_average,
                    'strongest_subjects': strongest_subjects,
                    'medium_subjects': medium_subjects,
                    'weakest_subjects': weakest_subjects,
                    'comments_and_advice': comments_and_advice,
                }

            if class_students_data:
                trends_data[student_class.name] = class_students_data

        cache.set(cache_key, trends_data, timeout=3600)  # Cache for 1 hour
        return trends_data

    except Exception as e:
        logger.error(f"Error in draw_student_trends_in_classes: {str(e)}", exc_info=True)
        return {}

############################################
# Subject Trends for Class
############################################

def draw_subject_trends_for_class() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Draw interactive time-series line graphs for each subject in each class using Plotly.
    Returns a nested dictionary keyed by class name and subject name with their performance insights.
    """
    cache_key = "subject_trends_for_class"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        classes = StudentClass.objects.prefetch_related('result_set__subject').all()
        sessions = AcademicSession.objects.all()
        terms = AcademicTerm.objects.all()
        exams = ExamType.objects.all()

        class_subject_insights: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for student_class in classes:
            results = Result.objects.filter(current_class=student_class)
            subject_ids = results.values_list('subject', flat=True).distinct()
            subjects = Subject.objects.filter(pk__in=subject_ids)
            class_avg = float(results.aggregate(avg=Avg('average'))['avg'] or 0)

            subject_insights: Dict[str, Dict[str, Any]] = {}
            for subject in subjects:
                data = []
                for session in sessions:
                    for term in terms:
                        for exam in exams:
                            subject_results = results.filter(session=session, term=term, exam=exam, subject=subject)
                            if not subject_results.exists():
                                continue
                            avg_score = float(subject_results.aggregate(avg=Avg('average'))['avg'] or 0)
                            data.append({
                                'Session': session.name,
                                'Term': term.name,
                                'Exam': exam.name,
                                'Average': avg_score
                            })

                if not data:
                    subject_insights[subject.name] = {
                        'graph': None,
                        'latest_average': None,
                        'predicted_average': None,
                        'comments_and_advice': "No data available for this subject."
                    }
                    continue

                df = pd.DataFrame(data)
                df['Average'] = df['Average'].astype(float)
                df['Index'] = range(len(df))
                latest_average = df['Average'].iloc[-1]

                # Anomaly detection
                anomalies = detect_anomalies(df['Average'].values)

                x = df['Index'].values.reshape(-1, 1)
                y = df['Average'].values.reshape(-1, 1)
                model, model_type = use_advanced_model_if_possible(x, y)
                predicted_average = float(model.predict([[len(df)]])[0])

                over_and_over_avg = df['Average'].mean()
                z_score = float(stats.zscore([latest_average], df['Average'].values)[0])

                strongest_subjects, medium_subjects, weakest_subjects = [], [], []
                if over_and_over_avg > 80:
                    strongest_subjects = [subject.name]
                elif over_and_over_avg > 50:
                    medium_subjects = [subject.name]
                else:
                    weakest_subjects = [subject.name]

                comments_and_advice = generate_comments_and_advice(
                    over_and_over_avg, latest_average, strongest_subjects, medium_subjects, weakest_subjects, z_score, class_avg
                )

                # Interactive Plotly chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam'],
                    y=df['Average'],
                    name='Average',
                    marker_color='skyblue',
                    opacity=0.7
                ))
                fig.add_trace(go.Scatter(
                    x=df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam'],
                    y=df['Average'],
                    mode='lines+markers',
                    name='Trend Line',
                    line=dict(color='orange', width=2),
                    marker=dict(size=8)
                ))
                if anomalies:
                    fig.add_trace(go.Scatter(
                        x=[(df['Session'] + ' - ' + df['Term'] + ' - ' + df['Exam']).iloc[i] for i in anomalies],
                        y=[df['Average'].iloc[i] for i in anomalies],
                        mode='markers',
                        name='Anomalies',
                        marker=dict(color='red', size=12, symbol='x')
                    ))

                fig.update_layout(
                    title=f"Subject Performance Trends for {subject.name} in {student_class.name} (Model: {model_type})",
                    xaxis_title="Session - Term - Exam",
                    yaxis_title="Average Score (Out of 100)",
                    xaxis_tickangle=-45,
                    title_font=dict(size=16, family="Poppins", color="#1B263B"),
                    showlegend=True,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=50, b=50)
                )
                fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

                image_base64 = _figure_to_base64(fig)

                subject_insights[subject.name] = {
                    'graph': image_base64,
                    'latest_average': latest_average,
                    'predicted_average': predicted_average,
                    'comments_and_advice': comments_and_advice
                }

            class_subject_insights[student_class.name] = subject_insights

        cache.set(cache_key, class_subject_insights, timeout=3600)  # Cache for 1 hour
        return class_subject_insights

    except Exception as e:
        logger.error(f"Error in draw_subject_trends_for_class: {str(e)}", exc_info=True)
        return {}

############################################
# Salary Distribution Charts
############################################

def draw_salary_distribution_charts() -> Tuple[
    Optional[str], Optional[str], Optional[str], Dict[str, float], List[Dict[str, Any]], float
]:
    """
    Generates interactive salary distribution charts by occupation and staff members using Plotly.
    Returns occupation chart, staff chart, error message, occupation distribution, staff distribution, and total salary.
    """
    cache_key = "salary_distribution_charts"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        staff_members = Staff.objects.filter(current_status="active")
        if not staff_members.exists():
            return None, None, "No active staff members to analyze.", {}, [], 0

        total_salary = staff_members.aggregate(total=Sum('salary'))['total'] or 0
        if total_salary == 0:
            return None, None, "No salary data available to analyze.", {}, [], 0

        total_salary_float = float(total_salary)
        occupations = staff_members.values_list('occupation', flat=True).distinct()
        salary_by_occupation = {
            occupation: float(staff_members.filter(occupation=occupation).aggregate(total=Sum('salary'))['total'] or 0)
            for occupation in occupations
        }

        salary_by_staff = list(staff_members.values('firstname', 'middle_name', 'surname', 'salary').order_by('-salary'))

        # Occupation chart
        occupation_labels = [o.title().replace("_", " ") for o in salary_by_occupation.keys()]
        occupation_percentages = [(s / total_salary_float) * 100 for s in salary_by_occupation.values()]

        fig_occ = go.Figure(data=[
            go.Pie(
                labels=occupation_labels,
                values=occupation_percentages,
                textinfo='percent+label',
                marker=dict(colors=px.colors.qualitative.Set3),
                hoverinfo='label+percent+value',
                textposition='inside'
            )
        ])
        fig_occ.update_layout(
            title="Salary Distribution by Occupation",
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=20)
        )
        occupation_chart = _figure_to_base64(fig_occ)

        # Staff chart
        staff_percentages = [(float(s['salary']) / total_salary_float) * 100 for s in salary_by_staff]
        staff_labels = [f"{s['firstname']} {s['middle_name']} {s['surname']}" for s in salary_by_staff]

        fig_staff = go.Figure(data=[
            go.Pie(
                labels=staff_labels,
                values=staff_percentages,
                textinfo='percent+label',
                marker=dict(colors=px.colors.qualitative.Pastel),
                hoverinfo='label+percent+value',
                textposition='inside'
            )
        ])
        fig_staff.update_layout(
            title="Salary Distribution by Staff",
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=20)
        )
        staff_chart = _figure_to_base64(fig_staff)

        cache.set(cache_key, (occupation_chart, staff_chart, None, salary_by_occupation, list(salary_by_staff), total_salary_float), timeout=3600)
        return occupation_chart, staff_chart, None, salary_by_occupation, list(salary_by_staff), total_salary_float

    except Exception as e:
        logger.error(f"Error in draw_salary_distribution_charts: {str(e)}", exc_info=True)
        return None, None, f"Error analyzing salary distribution: {str(e)}", {}, [], 0

############################################
# Salary Variation Over Time
############################################

def draw_salary_variation_line_chart() -> Tuple[Optional[str], Optional[QuerySet], Optional[str]]:
    """
    Plots the variation of total salary given each year-month using Plotly with ARIMA forecasting.
    Returns a base64 graph, salary data, and an error message if any.
    """
    cache_key = "salary_variation_line_chart"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        salary_data = (
            SalaryInvoice.objects.values("month")
            .annotate(total_given_salary=Sum("total_given_salary"))
            .order_by("month")
        )

        if not salary_data.exists():
            return None, None, "No salary data available to analyze."

        df = pd.DataFrame(list(salary_data))
        df['month'] = pd.to_datetime(df['month'])
        df = df.set_index('month')
        df['total_given_salary'] = df['total_given_salary'].astype(float)

        # ARIMA forecasting
        if len(df) > 3:
            arima_model = ARIMA(df['total_given_salary'], order=(1, 1, 1))
            arima_fit = arima_model.fit()
            forecast = arima_fit.forecast(steps=3)
            forecast_dates = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1), periods=3, freq='M')
            forecast_df = pd.DataFrame({'total_given_salary': forecast.values}, index=forecast_dates)
            combined_df = pd.concat([df, forecast_df])
        else:
            combined_df = df
            forecast_dates = []

        # Anomaly detection
        anomalies = detect_anomalies(df['total_given_salary'].values)
        anomaly_dates = [df.index[i].strftime("%Y-%m") for i in anomalies]

        # Interactive Plotly chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index.strftime("%Y-%m"),
            y=df['total_given_salary'],
            mode='lines+markers',
            name='Total Given Salary',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
        if len(forecast_dates) > 0:
            fig.add_trace(go.Scatter(
                x=combined_df.index[-3:].strftime("%Y-%m"),
                y=combined_df['total_given_salary'].iloc[-3:],
                mode='lines+markers',
                name='Forecast',
                line=dict(color='green', width=2, dash='dash'),
                marker=dict(size=8)
            ))
        if anomalies:
            fig.add_trace(go.Scatter(
                x=anomaly_dates,
                y=[df['total_given_salary'].iloc[i] for i in anomalies],
                mode='markers',
                name='Anomalies',
                marker=dict(color='red', size=12, symbol='x')
            ))

        fig.update_layout(
            title="Variation of Total Salary Given Across Year-Month",
            xaxis_title="Year-Month",
            yaxis_title="Total Given Salary (TZS)",
            xaxis_tickangle=-45,
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=50)
        )
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

        graph_base64 = _figure_to_base64(fig)
        cache.set(cache_key, (graph_base64, salary_data, None), timeout=3600)
        return graph_base64, salary_data, None

    except Exception as e:
        logger.error(f"Error in draw_salary_variation_line_chart: {str(e)}", exc_info=True)
        return None, None, f"Error analyzing salary variation: {str(e)}"

############################################
# Expenditure Heatmap and Waterfall
############################################
def expenditure_heatmap_waterfall() -> tuple[
    Optional[str], Optional[str],
    float, Dict[str, float], float, str, Optional[str]
]:
    """
    Build (heat-map, waterfall) showing how yearly income from receipts has
    been consumed by Expenditure / Purchases / Processing fees.
    """
    cache_key = "exp_heatmap_waterfall_v2"
    if (cached := cache.get(cache_key)):
        return cached

    try:
        current_year  = THIS_YEAR
        # income is total receipts
        total_income  = float(
            Receipt.objects.filter(date_paid__year=current_year)
                           .aggregate(t=Sum("amount_paid"))['t'] or 0
        )

        # spend = direct expenditures + seasonal purchases + processing fees
        spend_direct  = float(
            Expenditure.objects.filter(date__year=current_year)
                               .aggregate(t=Sum("amount"))['t'] or 0
        )
        cost_expr     = Sum('quantity') * Sum('price_per_unit')  # pseudo; we’ll calc below
        spend_pur     = float(
            SeasonalPurchase.objects.filter(date__year=current_year)
                .aggregate(t=Sum('quantity') * 0)['t'] or 0     # placeholder, we fix just below
        )
        # more precise purchase cost
        spend_pur = float(
            sum(p.quantity * p.price_per_unit
                for p in SeasonalPurchase.objects.filter(date__year=current_year))
        )
        spend_proc    = float(
            ProcessingBatch.objects.filter(date__year=current_year)
                                   .aggregate(t=Sum("processing_fee"))['t'] or 0
        )

        total_spent   = spend_direct + spend_pur + spend_proc
        remaining     = total_income - total_spent

        # bucket dict for heat-map categories
        cat_dict = {
            "Direct Expenses": spend_direct,
            "Raw Purchases":   spend_pur,
            "Processing Fees": spend_proc,
        }

        # ── Heat-map figure
        heat_fig = px.imshow(
            pd.DataFrame(cat_dict, index=['Amount TZS']).astype(float),
            color_continuous_scale='Blues',
            text_auto=True, aspect="auto",
            labels={'x': 'Category', 'color': 'TZS Spent'}
        )
        heat_fig.update_layout(title="Year-to-date Expenditure Heat-map")

        # ── Water-fall figure
        wf_fig = go.Figure(go.Waterfall(
            x=['Income'] + list(cat_dict.keys()) + ['Remaining'],
            y=[total_income] + [-v for v in cat_dict.values()] + [remaining],
            measure=['absolute'] + ['relative']*len(cat_dict) + ['total'],
            decreasing=dict(marker_color='crimson'),
            increasing=dict(marker_color='green'),
            totals=dict(marker_color='blue')
        ))
        wf_fig.update_layout(title="Cash-flow Water-fall (Receipts → Spend)")

        heat_b64 = _fig_to_base64(heat_fig)
        wf_b64   = _fig_to_base64(wf_fig)
        desc     = (
            f"Income TZS {total_income:,.0f} – Spent TZS {total_spent:,.0f} "
            f"⇒ Balance TZS {remaining:,.0f}"
        )
        cache.set(
            cache_key,
            (heat_b64, wf_b64, total_income, cat_dict,
             remaining, desc, None),
            3600
        )
        return heat_b64, wf_b64, total_income, cat_dict, remaining, desc, None

    except Exception as exc:                # pragma: no cover
        logger.exception("Heat-map / Water-fall failed.")
        return None, None, 0.0, {}, 0.0, "", str(exc)


############################################
# Profit Distribution
############################################

def generate_profit_pie_chart() -> Tuple[Optional[str], Optional[str]]:
    """
    Generates an interactive pie chart showing profit distribution by source using Plotly.
    Returns pie chart and error message.
    """
    cache_key = "profit_pie_chart"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        current_session = AcademicSession.objects.filter(current=True).first()
        if not current_session:
            return None, "No current academic session available."

        total_receipts = float(Receipt.objects.filter(invoice__session=current_session).aggregate(total=Sum('amount_paid'))['total'] or 0)
        total_uniforms = float(StudentUniform.objects.filter(session=current_session).aggregate(total=Sum('amount'))['total'] or 0)

        overall_total = total_receipts + total_uniforms
        if overall_total == 0:
            return None, "No income data available for the current session."

        receipt_percentage = (total_receipts / overall_total) * 100
        uniform_percentage = (total_uniforms / overall_total) * 100

        fig = go.Figure(data=[
            go.Pie(
                labels=['Receipts', 'Uniform Sales'],
                values=[receipt_percentage, uniform_percentage],
                textinfo='percent+label',
                marker=dict(colors=['#007bff', '#ffc107']),
                hoverinfo='label+percent+value',
                textposition='inside'
            )
        ])
        fig.update_layout(
            title="Profit Distribution by Source",
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=20)
        )

        pie_chart_base64 = _figure_to_base64(fig)
        cache.set(cache_key, (pie_chart_base64, None), timeout=3600)
        return pie_chart_base64, None

    except Exception as e:
        logger.error(f"Error in generate_profit_pie_chart: {str(e)}", exc_info=True)
        return None, f"Error generating profit pie chart: {str(e)}"

############################################
# Expenses Analysis
############################################

# ---------------------------------------------------------------------------#
# 3. EXPENSES ANALYSIS (Pie chart)                                           #
# ---------------------------------------------------------------------------#
def expenses_analysis() -> tuple[
    Optional[str], float, float, float, str
]:
    """
    Salaries vs. operational expenditures for the current academic session.
    Uses Receipts for income; Salaries + Expenditure for out-goings.
    """
    cache_key = "expenses_pie_v2"
    if (cached := cache.get(cache_key)):
        return cached

    try:
        session = AcademicSession.objects.filter(current=True).first()
        if not session:
            return None, 0.0, 0.0, 0.0, "No active session."

        # salaries tied to session
        salaries = float(
            SalaryInvoice.objects.filter(session=session)
                                 .aggregate(t=Sum("total_given_salary"))['t'] or 0
        )

        # operational spend: all Expenditure within session year
        year      = timezone.localdate().year   # fallback if session has no date fields
        ops_spend = float(
            Expenditure.objects.filter(date__year=year)
                               .aggregate(t=Sum("amount"))['t'] or 0
        )
        total_out = salaries + ops_spend
        if total_out == 0:
            return None, salaries, ops_spend, 0.0, "No expense data."

        labels = ['Salaries', 'Operational Spend']
        values = [salaries, ops_spend]

        fig = go.Figure(go.Pie(
            labels=labels, values=values, textinfo='percent+label',
            marker=dict(colors=['#ff7f0e', '#1f77b4'])
        ))
        fig.update_layout(title=f"Expenses split – {session.name}")

        comments = (
            "Salaries dominate." if salaries > ops_spend else
            "Operational spend dominates."
        )

        chart = _fig_to_base64(fig)
        cache.set(cache_key, (chart, salaries, ops_spend, total_out, comments), 3600)
        return chart, salaries, ops_spend, total_out, comments

    except Exception as exc:                # pragma: no cover
        logger.exception("Expenses analysis failed.")
        return None, 0.0, 0.0, 0.0, str(exc)


# --------------------------------
############################################
# Linear Regression Graph for Financial Trends
############################################

def draw_linear_regression_graph() -> Tuple[
    Optional[str],
    List[Tuple[str, float, float, float]],
    float,
    float,
    float,
    str
]:
    """
    Draws an interactive financial trend graph with ARIMA forecasting using Plotly.
    Returns a regression graph (base64), balance data, predicted profit, predicted expenses, predicted balance, and comments.
    """
    cache_key = "linear_regression_graph"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        sessions = AcademicSession.objects.all().order_by('id')
        if not sessions.exists():
            return None, [], 0, 0, 0, "No session data available."

        balance_data = []
        for session in sessions:
            total_receipts = float(Receipt.objects.filter(invoice__session=session).aggregate(sum=Sum('amount_paid'))['sum'] or 0)
            total_uniforms = float(StudentUniform.objects.filter(session=session).aggregate(sum=Sum('amount'))['sum'] or 0)
            total_income = total_receipts + total_uniforms

            total_salaries = float(SalaryInvoice.objects.filter(session=session).aggregate(sum=Sum('total_given_salary'))['sum'] or 0)
            total_expenditure_invoices = float(ExpenditureInvoice.objects.filter(session=session).aggregate(sum=Sum('initial_balance'))['sum'] or 0)
            total_expenses = total_salaries + total_expenditure_invoices

            balance = total_income - total_expenses
            if total_income > 0 or total_expenses > 0:
                balance_data.append((session.name, balance, total_income, total_expenses))

        if not balance_data:
            return None, [], 0, 0, 0, "No financial data found in any sessions."

        if len(balance_data) == 1:
            session_name, balance, profit, expenses = balance_data[0]
            predicted_profit = profit
            predicted_expenses = expenses
            predicted_balance = balance

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[session_name],
                y=[balance],
                mode='markers',
                name='Actual Balance',
                marker=dict(color='blue', size=12)
            ))
            fig.add_trace(go.Scatter(
                x=[session_name, session_name],
                y=[0, balance],
                mode='lines',
                name='Flat Trend',
                line=dict(color='red', dash='dash')
            ))
            fig.update_layout(
                title='Balance Trends Across Sessions',
                xaxis_title='Session',
                yaxis_title='Balance (TZS)',
                title_font=dict(size=16, family="Poppins", color="#1B263B"),
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=50, b=50)
            )
            fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

            regression_graph = _figure_to_base64(fig)
            regression_comments = (
                f"Only one session ({session_name}) of data. Current balance: {balance:,.2f} TZS. "
                "No trend can be established yet."
            )
            return regression_graph, balance_data, predicted_profit, predicted_expenses, predicted_balance, regression_comments

        df = pd.DataFrame(balance_data, columns=['Session', 'Balance', 'Profit', 'Expenses'])
        df['Session_Number'] = range(1, len(df) + 1)
        df['Balance'] = df['Balance'].astype(float)
        df['Profit'] = df['Profit'].astype(float)
        df['Expenses'] = df['Expenses'].astype(float)

        # ARIMA forecasting for balance
        if len(df) > 3:
            arima_model = ARIMA(df['Balance'], order=(1, 1, 1))
            arima_fit = arima_model.fit()
            forecast = arima_fit.forecast(steps=1)
            predicted_balance = float(forecast.iloc[0])
            predicted_profit = float(df['Profit'].iloc[-1])
            predicted_expenses = float(df['Expenses'].iloc[-1])
            forecast_session = f"Next Session"
        else:
            x = df['Session_Number'].values.reshape(-1, 1)
            y = df['Balance'].values.reshape(-1, 1)
            model, _ = use_advanced_model_if_possible(x, y)
            predicted_balance = float(model.predict([[len(df) + 1]])[0])
            predicted_profit = float(df['Profit'].iloc[-1])
            predicted_expenses = float(df['Expenses'].iloc[-1])
            forecast_session = f"Next Session"

        # Anomaly detection
        anomalies = detect_anomalies(df['Balance'].values)
        anomaly_sessions = [df['Session'].iloc[i] for i in anomalies]

        # Interactive Plotly chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Session'],
            y=df['Balance'],
            mode='markers',
            name='Actual Balance',
            marker=dict(color='blue', size=12)
        ))
        fig.add_trace(go.Scatter(
            x=df['Session'].tolist() + [forecast_session],
            y=df['Balance'].tolist() + [predicted_balance],
            mode='lines+markers',
            name='Trend Line',
            line=dict(color='red', dash='dash'),
            marker=dict(size=8)
        ))
        if anomalies:
            fig.add_trace(go.Scatter(
                x=anomaly_sessions,
                y=[df['Balance'].iloc[i] for i in anomalies],
                mode='markers',
                name='Anomalies',
                marker=dict(color='red', size=12, symbol='x')
            ))
        fig.add_trace(go.Scatter(
            x=[df['Session'].iloc[0], df['Session'].iloc[-1]],
            y=[0, 0],
            mode='lines',
            name='Zero Line',
            line=dict(color='gray', width=1, dash='dash')
        ))

        fig.update_layout(
            title='Balance Trends Across Sessions',
            xaxis_title='Session',
            yaxis_title='Balance (TZS)',
            xaxis_tickangle=-45,
            title_font=dict(size=16, family="Poppins", color="#1B263B"),
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=50, b=50)
        )
        fig.update_yaxes(gridcolor='rgba(0,0,0,0.1)')

        regression_graph = _figure_to_base64(fig)

        slope = predicted_balance - df['Balance'].iloc[-1]
        if slope > 0:
            regression_comments = (
                f"Positive trend ({slope:,.2f}/session): Financial health is improving. "
                "Continue current strategies and explore growth opportunities."
            )
        elif slope < 0:
            regression_comments = (
                f"Negative trend ({slope:,.2f}/session): Financial health is declining. "
                "Implement cost-saving measures and review revenue streams."
            )
        else:
            regression_comments = (
                "Stable trend: No significant change. Plan for potential future expenses."
            )

        cache.set(cache_key, (regression_graph, balance_data, predicted_profit, predicted_expenses, predicted_balance, regression_comments), timeout=3600)
        return regression_graph, balance_data, predicted_profit, predicted_expenses, predicted_balance, regression_comments

    except Exception as e:
        logger.error(f"Error in draw_linear_regression_graph: {str(e)}", exc_info=True)
        return None, [], 0, 0, 0, f"Error analyzing financial trends: {str(e)}"