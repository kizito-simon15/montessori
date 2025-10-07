// script.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('modernForm');
    
    form.addEventListener('submit', (e) => {
        e.preventDefault(); // Prevent page reload
        const inputs = Array.from(form.querySelectorAll('input'));
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.style.border = '2px solid red';
                setTimeout(() => input.style.border = '', 2000);
            }
        });
    });
});
