import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

import numpy as np
import pandas as pd
from django.db.models import Sum, QuerySet
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages

from .utils import (
    draw_class_performance_trends,
    draw_subject_trends_for_class,
    draw_student_trends_in_classes,
    draw_salary_distribution_charts,
    draw_salary_variation_line_chart,
    draw_expenditure_heatmap_and_waterfall,
    draw_expenses_analysis,
    draw_linear_regression_graph,
    generate_profit_pie_chart,
    cluster_subjects_by_performance,
    detect_anomalies
)

from apps.finance.models import Receipt, StudentUniform
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass
from apps.students.models import Student
from apps.result.models import Result
from expenditures.models import ExpenditureInvoice

logger = logging.getLogger(__name__)

def analytics_home(request: HttpRequest) -> HttpResponse:
    """
    Landing page for the analytics section, providing quick links to academic and finance analytics pages.
    Includes a summary of key metrics for quick insight.
    """
    logger.debug("Rendering analytics home page.")
    context = {}

    try:
        # Quick Academic Metrics
        classes = StudentClass.objects.all()
        total_students = Student.objects.count()
        total_classes = classes.count()
        results = Result.objects.exclude(average__isnull=True)
        avg_performance = float(results.aggregate(avg=Sum('average'))['avg'] / results.count()) if results.exists() else 0

        # Quick Financial Metrics
        current_session = AcademicSession.objects.filter(current=True).first()
        if current_session:
            total_income = (
                float(Receipt.objects.filter(invoice__session=current_session).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0) +
                float(StudentUniform.objects.filter(session=current_session).aggregate(Sum('amount'))['amount__sum'] or 0)
            )
            total_expenses = float(ExpenditureInvoice.objects.filter(session=current_session).aggregate(Sum('initial_balance'))['initial_balance__sum'] or 0)
            financial_balance = total_income - total_expenses
        else:
            total_income = total_expenses = financial_balance = 0

        context.update({
            'total_students': total_students,
            'total_classes': total_classes,
            'avg_performance': avg_performance,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'financial_balance': financial_balance,
            'current_session': current_session.name if current_session else "No Active Session",
        })
    except Exception as e:
        logger.error(f"Error fetching analytics home metrics: {e}", exc_info=True)
        messages.error(request, "Unable to load summary metrics.")

    return render(request, 'analytics/home.html', context)

def academic_analysis(request: HttpRequest) -> HttpResponse:
    """
    Academic analytics main view, providing links or brief overviews of academic metrics.
    Includes top-performing classes and subjects needing attention.
    """
    logger.debug("Rendering academic_analysis view.")
    context = {}

    try:
        # Top Performing Classes
        class_graphs = draw_class_performance_trends()
        top_classes = sorted(
            [(cls, data['latest_average']) for cls, data in class_graphs.items() if data['latest_average']],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Subjects Needing Attention (from clustering)
        _, cluster_labels, _ = cluster_subjects_by_performance()
        low_performing_subjects = [subj for subj, cluster in cluster_labels.items() if cluster == 'Low']

        context.update({
            'top_classes': top_classes,
            'low_performing_subjects': low_performing_subjects,
        })
    except Exception as e:
        logger.error(f"Error in academic_analysis: {e}", exc_info=True)
        messages.error(request, "Unable to load academic overview data.")

    return render(request, 'analytics/academic_analysis.html', context)

def finance_analysis(request: HttpRequest) -> HttpResponse:
    """
    Finance analytics main view, offering summaries and links to detailed views.
    Includes financial health metrics and recent anomalies.
    """
    logger.debug("Rendering finance_analysis view.")
    context = {}

    try:
        # Financial Health Summary
        current_session = AcademicSession.objects.filter(current=True).first()
        if current_session:
            total_income = (
                float(Receipt.objects.filter(invoice__session=current_session).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0) +
                float(StudentUniform.objects.filter(session=current_session).aggregate(Sum('amount'))['amount__sum'] or 0)
            )
            total_expenses = float(ExpenditureInvoice.objects.filter(session=current_session).aggregate(Sum('initial_balance'))['initial_balance__sum'] or 0)
            financial_balance = total_income - total_expenses
        else:
            total_income = total_expenses = financial_balance = 0

        # Recent Salary Anomalies
        _, salary_variation_data, _ = draw_salary_variation_line_chart()
        if salary_variation_data:
            df = pd.DataFrame(list(salary_variation_data))
            df['month'] = pd.to_datetime(df['month'])
            df['total_given_salary'] = df['total_given_salary'].astype(float)
            anomalies = detect_anomalies(df['total_given_salary'].values)
            anomaly_dates = [df['month'].iloc[i].strftime("%Y-%m") for i in anomalies][:3]  # Top 3 anomalies
        else:
            anomaly_dates = []

        context.update({
            'total_income': total_income,
            'total_expenses': total_expenses,
            'financial_balance': financial_balance,
            'current_session': current_session.name if current_session else "No Active Session",
            'recent_salary_anomalies': anomaly_dates,
        })
    except Exception as e:
        logger.error(f"Error in finance_analysis: {e}", exc_info=True)
        messages.error(request, "Unable to load financial overview data.")

    return render(request, 'analytics/finance_analysis.html', context)

def class_performance_view(request: HttpRequest) -> HttpResponse:
    """
    Renders performance trends for all classes with anomalies and class comparisons.
    """
    logger.debug("Generating class performance trends.")
    graphs = draw_class_performance_trends()
    if not graphs:
        messages.error(request, "No performance data available for any class.")
        return render(request, 'analytics/performance_trends.html', {'message': "No performance data available for any class."})

    no_data = all(v['graph'] is None for v in graphs.values())
    if no_data:
        messages.warning(request, "No data for classes.")
        return render(request, 'analytics/performance_trends.html', {'message': "No data for classes."})

    # Add class average comparison
    class_averages = {cls: data['latest_average'] for cls, data in graphs.items() if data['latest_average']}
    overall_avg = sum(class_averages.values()) / len(class_averages) if class_averages else 0

    context = {
        'graphs': graphs,
        'overall_avg': overall_avg,
        'class_averages': class_averages,
    }
    return render(request, 'analytics/performance_trends.html', context)

def subject_trends_view(request: HttpRequest) -> HttpResponse:
    """
    Displays subject trends for each class with anomalies and intervention suggestions.
    """
    logger.debug("Generating subject trends for each class.")
    subject_trends = draw_subject_trends_for_class()
    if not subject_trends:
        messages.error(request, "No subject trend data available.")
        return render(request, 'analytics/subject_trends.html', {'message': "No subject trend data available."})

    no_data_classes = [cls for cls, subjects in subject_trends.items() if not subjects]
    if no_data_classes:
        messages.warning(request, f"Some classes have no subject trend data: {', '.join(no_data_classes)}")

    # Identify subjects needing intervention
    intervention_subjects = {}
    for cls, subjects in subject_trends.items():
        for subj, data in subjects.items():
            if data['latest_average'] and data['latest_average'] < 50:
                intervention_subjects.setdefault(cls, []).append(subj)

    context = {
        'subject_trends': subject_trends,
        'no_data_classes': no_data_classes,
        'intervention_subjects': intervention_subjects,
    }
    return render(request, 'analytics/subject_trends.html', context)

def student_trends_view(request: HttpRequest) -> HttpResponse:
    """
    Displays student performance trends with z-scores, anomalies, and class comparisons.
    """
    logger.debug("Generating student trends.")
    student_trends = draw_student_trends_in_classes()
    if not student_trends:
        messages.error(request, "No student trend data available.")
        return render(request, 'analytics/student_trends.html', {'message': "No student trend data available."})

    # Add class averages for comparison
    class_averages = {}
    for cls, students in student_trends.items():
        student_averages = [data['latest_average'] for data in students.values() if data['latest_average']]
        class_averages[cls] = sum(student_averages) / len(student_averages) if student_averages else 0

    context = {
        'student_trends': student_trends,
        'class_averages': class_averages,
    }
    return render(request, 'analytics/student_trends.html', context)

def subject_clustering_view(request: HttpRequest) -> HttpResponse:
    """
    Displays clusters of subjects by performance with intervention recommendations.
    """
    logger.debug("Clustering subjects by performance.")
    cluster_chart, cluster_labels, error = cluster_subjects_by_performance()
    if error:
        messages.error(request, error)
        return render(request, 'analytics/subject_clusters.html', {'message': error})

    # Intervention recommendations based on clusters
    intervention_recommendations = {
        'Low': "Immediate intervention required: schedule extra classes and tutoring.",
        'Medium': "Moderate performance: assign targeted homework and monitor progress.",
        'High': "High performance: encourage advanced projects or peer mentoring."
    }

    context = {
        'cluster_chart': cluster_chart,
        'cluster_labels': cluster_labels,
        'intervention_recommendations': intervention_recommendations,
    }
    return render(request, 'analytics/subject_clusters.html', context)

def salary_distribution_view(request: HttpRequest) -> HttpResponse:
    """
    Shows salary distribution by occupation and staff, with variation over time and anomaly alerts.
    """
    logger.debug("Generating salary distribution and variation charts.")
    (occupation_chart, staff_chart, error_message,
     salary_by_occupation, salary_by_staff, total_salary) = draw_salary_distribution_charts()

    salary_variation_chart, salary_variation_data, salary_variation_error = draw_salary_variation_line_chart()

    combined_error = error_message or salary_variation_error
    if combined_error:
        messages.warning(request, combined_error)

    # Financial health insight
    if total_salary:
        avg_salary = total_salary / len(salary_by_staff) if salary_by_staff else 0
        salary_health = "Stable" if avg_salary > 500000 else "Low"  # Example threshold (500,000 TZS)
    else:
        salary_health = "No data"

    context = {
        'occupation_chart': occupation_chart,
        'staff_chart': staff_chart,
        'error_message': combined_error,
        'salary_by_occupation': salary_by_occupation,
        'salary_by_staff': salary_by_staff,
        'total_salary': total_salary,
        'salary_variation_chart': salary_variation_chart,
        'salary_variation_data': salary_variation_data,
        'salary_health': salary_health,
        'avg_salary': avg_salary if total_salary else 0,
    }
    return render(request, 'analytics/salary_distribution.html', context)

def expenditure_analysis_view(request: HttpRequest) -> HttpResponse:
    """
    Displays expenditure analysis with heatmap, waterfall charts, and financial health insights.
    """
    logger.debug("Generating expenditure analysis charts.")
    (heatmap, waterfall, total_initial_balance, category_expenditures,
     remaining_balance, trend_description, error_message) = draw_expenditure_heatmap_and_waterfall()

    current_year = datetime.now().year

    if error_message:
        messages.warning(request, error_message)

    # Categorize financial health
    if remaining_balance > 0:
        financial_health = "Healthy"
    elif remaining_balance < 0:
        financial_health = "At Risk"
    else:
        financial_health = "Balanced"

    context = {
        'heatmap': heatmap,
        'waterfall': waterfall,
        'total_initial_balance': total_initial_balance,
        'category_expenditures': category_expenditures,
        'remaining_balance': remaining_balance,
        'trend_description': trend_description,
        'error_message': error_message,
        'current_year': current_year,
        'financial_health': financial_health,
    }
    return render(request, 'analytics/expenditure_analysis.html', context)

def profit_analysis_view(request: HttpRequest) -> HttpResponse:
    """
    Analyzes profit distribution, expenses, and uses regression for future balance predictions.
    Includes financial health metrics and forecast insights.
    """
    logger.debug("Generating profit analysis.")
    current_session = AcademicSession.objects.filter(current=True).first()
    if not current_session:
        messages.error(request, "No active academic session found for profit analysis.")
        return render(request, 'analytics/profit_analysis.html', {
            'error_message': "No active session found."
        })

    profit_pie_chart, profit_chart_error = generate_profit_pie_chart()
    if profit_chart_error:
        messages.warning(request, profit_chart_error)
        return render(request, 'analytics/profit_analysis.html', {'error_message': profit_chart_error})

    total_receipts = float(Receipt.objects.filter(invoice__session=current_session).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0)
    total_uniforms = float(StudentUniform.objects.filter(session=current_session).aggregate(Sum('amount'))['amount__sum'] or 0)
    overall_total_income = total_receipts + total_uniforms

    if total_receipts > total_uniforms * 2:
        profit_comments = "Receipts significantly dominate income. Diversify revenue through uniform sales or other streams."
    elif total_uniforms > total_receipts * 2:
        profit_comments = "Uniform sales dominate income. Enhance receipt collections to balance revenue sources."
    else:
        profit_comments = "Receipts and uniform sales are relatively balanced. Continue monitoring for optimal diversification."

    (expenses_pie_chart, total_salaries, total_expenditures, overall_total_expenses,
     expenses_comments) = draw_expenses_analysis()

    (regression_graph, balance_data, predicted_profit, predicted_expenses,
     predicted_balance, regression_comments) = draw_linear_regression_graph()

    remaining_balance = overall_total_income - overall_total_expenses
    if remaining_balance > 0:
        balance_comments = (
            f"Surplus of TZS {remaining_balance:,.2f}. Financial health is strong. "
            "Consider investing in infrastructure or student programs."
        )
    elif remaining_balance < 0:
        balance_comments = (
            f"Deficit of TZS {abs(remaining_balance):,.2f}. Financial health at risk. "
            "Implement cost controls or increase revenue."
        )
    else:
        balance_comments = (
            f"Balanced at TZS {remaining_balance:,.2f}. Financially stable. "
            "Plan for future growth to build a surplus."
        )

    # Financial health based on predicted balance
    financial_health = "Positive" if predicted_balance > 0 else "Negative" if predicted_balance < 0 else "Neutral"

    context = {
        'current_session': current_session.name,
        'profit_pie_chart': profit_pie_chart,
        'total_receipts': total_receipts,
        'total_uniforms': total_uniforms,
        'overall_total_income': overall_total_income,
        'profit_comments': profit_comments,
        'expenses_pie_chart': expenses_pie_chart,
        'total_salaries': total_salaries,
        'total_expenditures': total_expenditures,
        'overall_total_expenses': overall_total_expenses,
        'expenses_comments': expenses_comments,
        'remaining_balance': remaining_balance,
        'balance_comments': balance_comments,
        'regression_graph': regression_graph,
        'balance_data': balance_data,
        'predicted_profit': predicted_profit,
        'predicted_expenses': predicted_expenses,
        'predicted_balance': predicted_balance,
        'regression_comments': regression_comments,
        'financial_health': financial_health,
    }
    return render(request, 'analytics/profit_analysis.html', context)

def comprehensive_analytics_view(request: HttpRequest) -> HttpResponse:
    """
    Provides a comprehensive dashboard with academic and financial analytics, including key insights.
    """
    logger.debug("Generating a comprehensive analytics overview.")
    context = {}

    try:
        # Academic Insights
        class_graphs = draw_class_performance_trends()
        student_trends = draw_student_trends_in_classes()
        _, cluster_labels, _ = cluster_subjects_by_performance()

        top_classes = sorted(
            [(cls, data['latest_average']) for cls, data in class_graphs.items() if data['latest_average']],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        low_performing_subjects = [subj for subj, cluster in cluster_labels.items() if cluster == 'Low']

        # High-Risk Students (based on z-score or latest average < 50)
        high_risk_students = []
        for cls, students in student_trends.items():
            for student_id, data in students.items():
                if data['latest_average'] < 50 or data['comments_and_advice'].lower().find("urgent") != -1:
                    high_risk_students.append({
                        'class': cls,
                        'name': data['name'],
                        'latest_average': data['latest_average'],
                        'advice': data['comments_and_advice']
                    })
        high_risk_students = sorted(high_risk_students, key=lambda x: x['latest_average'])[:5]

        context.update({
            'class_graphs': class_graphs,
            'top_classes': top_classes,
            'low_performing_subjects': low_performing_subjects,
            'high_risk_students': high_risk_students,
        })
    except Exception as e:
        logger.error(f"Error fetching academic insights: {e}", exc_info=True)
        messages.error(request, "Unable to load academic insights.")

    try:
        # Financial Insights
        profit_pie_chart, _ = generate_profit_pie_chart()
        (expenses_pie_chart, total_salaries, total_expenditures, overall_total_expenses,
         expenses_comments) = draw_expenses_analysis()
        (regression_graph, balance_data, predicted_profit, predicted_expenses,
         predicted_balance, regression_comments) = draw_linear_regression_graph()

        current_session = AcademicSession.objects.filter(current=True).first()
        if current_session:
            total_income = (
                float(Receipt.objects.filter(invoice__session=current_session).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0) +
                float(StudentUniform.objects.filter(session=current_session).aggregate(Sum('amount'))['amount__sum'] or 0)
            )
            remaining_balance = total_income - overall_total_expenses
        else:
            total_income = remaining_balance = 0

        context.update({
            'profit_pie_chart': profit_pie_chart,
            'expenses_pie_chart': expenses_pie_chart,
            'total_salaries': total_salaries,
            'total_expenditures': total_expenditures,
            'overall_total_expenses': overall_total_expenses,
            'expenses_comments': expenses_comments,
            'total_income': total_income,
            'remaining_balance': remaining_balance,
            'regression_graph': regression_graph,
            'balance_data': balance_data,
            'predicted_profit': predicted_profit,
            'predicted_expenses': predicted_expenses,
            'predicted_balance': predicted_balance,
            'regression_comments': regression_comments,
        })
    except Exception as e:
        logger.error(f"Error fetching financial insights: {e}", exc_info=True)
        messages.error(request, "Unable to load financial insights.")

    return render(request, 'analytics/comprehensive_dashboard.html', context)

def student_comparison_view(request: HttpRequest, class_id: int) -> HttpResponse:
    """
    Compares student performance within a specified class against the class average.
    Highlights outliers and provides intervention suggestions.
    """
    logger.debug(f"Generating student comparison for class ID {class_id}.")
    student_class = get_object_or_404(StudentClass, id=class_id)
    student_trends = draw_student_trends_in_classes()

    class_trends = student_trends.get(student_class.name, {})
    if not class_trends:
        messages.error(request, f"No student trend data available for class {student_class.name}.")
        return render(request, 'analytics/student_comparison.html', {
            'class_name': student_class.name,
            'message': "No student trend data available."
        })

    # Calculate class average and identify outliers
    student_averages = [data['latest_average'] for data in class_trends.values() if data['latest_average']]
    class_avg = sum(student_averages) / len(student_averages) if student_averages else 0
    outliers = [
        (data['name'], data['latest_average'], data['comments_and_advice'])
        for student_id, data in class_trends.items()
        if data['latest_average'] and (data['latest_average'] < class_avg - 10 or data['latest_average'] > class_avg + 10)
    ]

    context = {
        'class_name': student_class.name,
        'students': class_trends,
        'class_avg': class_avg,
        'outliers': outliers,
    }
    return render(request, 'analytics/student_comparison.html', context)

def subject_intervention_view(request: HttpRequest) -> HttpResponse:
    """
    Identifies subjects needing intervention across all classes and provides actionable recommendations.
    """
    logger.debug("Generating subject intervention analysis.")
    subject_trends = draw_subject_trends_for_class()
    if not subject_trends:
        messages.error(request, "No subject trend data available for intervention analysis.")
        return render(request, 'analytics/subject_intervention.html', {'message': "No subject trend data available."})

    # Identify subjects needing intervention (latest_average < 50 or declining trend)
    intervention_list = []
    for cls, subjects in subject_trends.items():
        for subj, data in subjects.items():
            if data['latest_average'] and (data['latest_average'] < 50 or data['predicted_average'] < data['latest_average']):
                intervention_list.append({
                    'class': cls,
                    'subject': subj,
                    'latest_average': data['latest_average'],
                    'predicted_average': data['predicted_average'],
                    'comments': data['comments_and_advice']
                })

    intervention_list = sorted(intervention_list, key=lambda x: x['latest_average'])

    context = {
        'intervention_list': intervention_list,
    }
    return render(request, 'analytics/subject_intervention.html', context)

def financial_forecast_view(request: HttpRequest) -> HttpResponse:
    """
    Provides a detailed financial forecast dashboard with ARIMA predictions and anomaly alerts.
    """
    logger.debug("Generating financial forecast dashboard.")
    (regression_graph, balance_data, predicted_profit, predicted_expenses,
     predicted_balance, regression_comments) = draw_linear_regression_graph()

    (occupation_chart, staff_chart, _, salary_by_occupation, salary_by_staff,
     total_salary) = draw_salary_distribution_charts()

    salary_variation_chart, salary_variation_data, _ = draw_salary_variation_line_chart()

    # Financial health and risk assessment
    if predicted_balance > 0:
        financial_risk = "Low"
        risk_advice = "Continue current financial strategies and consider long-term investments."
    elif predicted_balance < 0:
        financial_risk = "High"
        risk_advice = "Urgent action required: reduce expenditures or increase revenue."
    else:
        financial_risk = "Moderate"
        risk_advice = "Maintain balance and prepare for potential expenses."

    context = {
        'regression_graph': regression_graph,
        'balance_data': balance_data,
        'predicted_profit': predicted_profit,
        'predicted_expenses': predicted_expenses,
        'predicted_balance': predicted_balance,
        'regression_comments': regression_comments,
        'occupation_chart': occupation_chart,
        'staff_chart': staff_chart,
        'salary_by_occupation': salary_by_occupation,
        'salary_by_staff': salary_by_staff,
        'total_salary': total_salary,
        'salary_variation_chart': salary_variation_chart,
        'salary_variation_data': salary_variation_data,
        'financial_risk': financial_risk,
        'risk_advice': risk_advice,
    }
    return render(request, 'analytics/financial_forecast.html', context)

def performance_overview_view(request: HttpRequest) -> HttpResponse:
    """
    Summarizes academic performance across all classes with filters for sessions, terms, and exams.
    """
    logger.debug("Generating performance overview.")
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exams = ExamType.objects.all()
    classes = StudentClass.objects.all()

    # Filter parameters
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    exam_id = request.GET.get('exam')

    context = {
        'sessions': sessions,
        'terms': terms,
        'exams': exams,
        'classes': classes,
        'selected_session': session_id,
        'selected_term': term_id,
        'selected_exam': exam_id,
    }

    try:
        results = Result.objects.exclude(average__isnull=True)
        if session_id:
            results = results.filter(session_id=session_id)
        if term_id:
            results = results.filter(term_id=term_id)
        if exam_id:
            results = results.filter(exam_id=exam_id)

        class_summaries = []
        for student_class in classes:
            class_results = results.filter(current_class=student_class)
            if not class_results.exists():
                continue

            student_averages = []
            distinct_students = class_results.values_list('student', flat=True).distinct()
            for student_id in distinct_students:
                student_res = class_results.filter(student_id=student_id)
                if student_res.exists():
                    avg_per_student = float(student_res.aggregate(a=Avg('average'))['a'])
                    student_averages.append(avg_per_student)

            if student_averages:
                class_avg = sum(student_averages) / len(student_averages)
                anomalies = detect_anomalies(np.array(student_averages))
                outlier_students = [
                    (Student.objects.get(id=student_id).get_full_name(), student_averages[i])
                    for i, student_id in enumerate(distinct_students)
                    if i in anomalies
                ]

                class_summaries.append({
                    'class_name': student_class.name,
                    'average': class_avg,
                    'total_students': len(distinct_students),
                    'outlier_students': outlier_students,
                })

        class_summaries = sorted(class_summaries, key=lambda x: x['average'], reverse=True)
        context['class_summaries'] = class_summaries
    except Exception as e:
        logger.error(f"Error in performance_overview_view: {e}", exc_info=True)
        messages.error(request, "Unable to load performance overview data.")

    return render(request, 'analytics/performance_overview.html', context)