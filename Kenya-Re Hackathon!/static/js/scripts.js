document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        resultDiv.innerHTML = 'Processing...';

        const formData = new FormData(form);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(htmlContent => {
            // Replace the current page content
            document.open();
            document.write(htmlContent);
            document.close();
            
            // Optional: Scroll to top of new content
            window.scrollTo(0, 0);
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = `An error occurred: ${error.message}`;
        });
    });
});