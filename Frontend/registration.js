// Listen for form submission 
document.getElementById('registrationForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the form from submitting normally (page reload)

    // Get values from the form inputs
    const name = document.getElementById('name').value;
    const address = document.getElementById('address').value;
    const phone = document.getElementById('phone').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const messageElement = document.getElementById('message'); // Element to show messages

    // Check if passwords match
    if (password !== confirmPassword) {
        messageElement.textContent = '❌ Passwords do not match.';
        messageElement.style.color = 'red';
        return; // Stop further execution
    }

    // Send a POST request to the backend API with user data
    fetch('http://localhost:5000/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json' // Sending data as JSON
        },
        body: JSON.stringify({ name, address, phone, email, password }) // Data payload
    })
    .then(response => response.json()) // Parse the JSON response
    .then(result => {
        // Show message from server (success or error)
        messageElement.textContent = result.message || result.error;
        messageElement.style.color = result.error ? 'red' : 'green';
    })
    .catch(error => {
        // Handle errors like server not reachable
        console.error('Error:', error);
        messageElement.textContent = '❌ Could not connect to server.';
        messageElement.style.color = 'red';
    });
});
