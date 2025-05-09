document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('birthdayCardForm');
    const dogPhotoInput = document.getElementById('dogPhoto');
    const imagePreview = document.getElementById('imagePreview');
    const fileUploadArea = document.querySelector('.file-upload-area');
    const resultsSection = document.getElementById('resultsSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const videoResultDiv = document.getElementById('videoResult');
    const errorResultDiv = document.getElementById('errorResult');
    const toggleAdvancedButton = document.getElementById('toggleAdvanced');
    const advancedOptionsDiv = document.getElementById('advancedOptions');

    // Trigger file input when custom upload area is clicked
    if (fileUploadArea) {
        fileUploadArea.addEventListener('click', () => {
            dogPhotoInput.click();
        });
    }

    // Handle file input change for preview
    if (dogPhotoInput) {
        dogPhotoInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                }
                reader.readAsDataURL(file);
                // Update text in upload area
                fileUploadArea.querySelector('.file-upload-visual p').textContent = file.name;
                fileUploadArea.querySelector('.file-upload-visual .file-types').textContent = 'Image selected';
            } else {
                imagePreview.style.display = 'none';
                fileUploadArea.querySelector('.file-upload-visual p').textContent = 'Click to upload or drag and drop';
                fileUploadArea.querySelector('.file-upload-visual .file-types').textContent = 'JPG, PNG, GIF (Max 5MB)';
            }
        });
    }
    
    // Toggle advanced options
    if (toggleAdvancedButton) {
        toggleAdvancedButton.addEventListener('click', () => {
            const isHidden = advancedOptionsDiv.style.display === 'none';
            advancedOptionsDiv.style.display = isHidden ? 'block' : 'none';
            toggleAdvancedButton.textContent = isHidden ? 'Hide Advanced Options 🔼' : 'Show Advanced Options 👇';
        });
    }

    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            resultsSection.style.display = 'block';
            loadingIndicator.style.display = 'block';
            videoResultDiv.innerHTML = ''; // Clear previous results
            errorResultDiv.style.display = 'none';
            errorResultDiv.textContent = '';

            const formData = new FormData(form);
            
            // Ensure use_local_storage is true, as the frontend expects to display results from server paths
            formData.set('use_local_storage', 'true');
            
            // Add birthdayMessage if it's empty, server might expect it
            if (!formData.has('birthdayMessage') || formData.get('birthdayMessage').trim() === '') {
                // The chibi_clip.py doesn't use birthdayMessage in prompts, so it's truly optional
                // No need to add it if empty.
            }

            // Default action if not set (though HTML select has a default)
            if (!formData.has('action')) {
                formData.set('action', 'birthday-dance');
            }
            if (!formData.has('ratio')) {
                formData.set('ratio', '9:16');
            }
            if (!formData.has('extended_duration')) {
                formData.set('extended_duration', '15'); // Default from HTML
            }
            // 'use_default_audio' is a checkbox, its value will be 'on' or absent.
            // The server handles "false".lower() == "true" for string false.
            // For FormData, unchecked checkboxes are not included.
            // If we want to explicitly send false if unchecked: Needs custom handling, 
            // but server default logic for get("param", "false") should be okay.

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData, // FormData handles multipart/form-data for file upload
                });

                loadingIndicator.style.display = 'none';

                if (!response.ok) {
                    let errorMsg = `Server error: ${response.status}`;
                    try {
                        const errData = await response.json();
                        errorMsg = errData.error || JSON.stringify(errData);
                    } catch (e) {
                        // If parsing error JSON fails, use the status text
                        errorMsg += ` - ${response.statusText}`;
                    }
                    throw new Error(errorMsg);
                }

                const result = await response.json();

                if (result.error) {
                    throw new Error(result.error);
                }

                let resultHTML = '';
                if (result.video_url) {
                     // Assuming server returns a path like /videos/filename.mp4
                    resultHTML += `<h3>Video Ready!</h3><video controls src="${result.video_url}"></video>`;
                }
                if (result.image_url && !result.video_url) { // if only image was generated (e.g. error before video)
                     // Assuming server returns a path like /images/filename.png
                    resultHTML += `<h3>Image Preview:</h3><img src="${result.image_url}" alt="Generated Image">`;
                }
                if (result.public_image_url_for_display && !result.video_url && !result.image_url) {
                    resultHTML += `<h3>Image Stored:</h3><img src="${result.public_image_url_for_display}" alt="Generated Image">`;
                }
                
                resultHTML += `<p>You can share this link: <a href="${result.video_url || result.image_url || result.public_image_url_for_display}" target="_blank">${result.video_url || result.image_url || result.public_image_url_for_display}</a></p>`;
                
                if (result.message) {
                    resultHTML += `<p>${result.message}</p>`;
                }

                videoResultDiv.innerHTML = resultHTML;

            } catch (error) {
                loadingIndicator.style.display = 'none';
                errorResultDiv.textContent = `An error occurred: ${error.message}`;
                errorResultDiv.style.display = 'block';
                console.error('Form submission error:', error);
            }
        });
    }
}); 