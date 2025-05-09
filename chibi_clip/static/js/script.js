document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('birthdayCardForm');
    const dogPhotoInput = document.getElementById('dogPhoto');
    const imagePreview = document.getElementById('imagePreview');
    const fileUploadArea = document.querySelector('.file-upload-area');
    const resultsSection = document.getElementById('resultsSection');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const videoResultDiv = document.getElementById('videoResult');
    const errorResultDiv = document.getElementById('errorResult');

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
                // Prioritize local_video_url (the extended one) if available
                const displayVideoUrl = result.local_video_url || result.video_url; 

                if (displayVideoUrl) {
                     resultHTML += `<h3>Video Ready!</h3><video controls src="${displayVideoUrl}"></video>`;
                }
                // Fallback for image if video URL isn't primary
                else if (result.image_url) { 
                    resultHTML += `<h3>Image Preview:</h3><img src="${result.image_url}" alt="Generated Image">`;
                }
                else if (result.public_image_url_for_display) { // Likely an alias for image_url if served locally
                    resultHTML += `<h3>Image Stored:</h3><img src="${result.public_image_url_for_display}" alt="Generated Image">`;
                }
                
                // The share link should also prioritize the video URL that's being displayed
                const shareUrl = displayVideoUrl || result.image_url || result.public_image_url_for_display;
                if (shareUrl) {
                    resultHTML += `<p>You can share this link: <a href="${shareUrl}" target="_blank">${shareUrl}</a></p>`;
                }
                
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