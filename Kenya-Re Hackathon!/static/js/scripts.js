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
            if (response.ok) {
                // Expecting a blob (binary data) for the PDF
                return response.blob(); 
            } else {
                throw new Error('Failed to process files');
            }
        })
        .then(blob => {
            // Create a temporary URL for the blob
            const url = window.URL.createObjectURL(blob);
            
            // Create a hidden link and click it to trigger the download
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'discrepancy_report.pdf';
            document.body.appendChild(a);
            a.click();
            
            // Clean up the temporary URL
            window.URL.revokeObjectURL(url);
            resultDiv.innerHTML = 'Download complete.';
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = 'An error occurred while processing the files.',error;
        });
    });
});