paypal
    .Buttons({
        style: {
            shape: "rect",
            layout: "vertical",
            color: "gold",
            label: "paypal",
        },

        createOrder: function(data, actions) {
	    const bookingId = document.getElementById('booking-id').value;
            return fetch(`/api/create-order/${bookingId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
		    'X-CSRFToken': getCookie('csrftoken'),
                },
            }).then(function(res) {
		return res.json();
	    }).then(function(orderData) {
		// Store the relevant URLs defined in the order
		sessionStorage.setItem('return_url', orderData.return_url);
		sessionStorage.setItem('cancel_url', orderData.cancel_url);
		return orderData.id;
	    });
	},

        onApprove: function(data, actions) {
            return fetch(
                `/api/capture-order/`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
			'X-CSRFToken': getCookie('csrftoken'),
                    },
		    body: JSON.stringify({
			orderID: data.orderID
		    })
		}).then(function(res) {
		    return res.json();
		}).then(function(orderData) {
		    console.log('Capture result', orderData);
		    window.location.href = sessionStorage.getItem('return_url'); // Redirect to the return URL
		});
	},
	onCancel: function(data, actions) {
            // Redirect to the cancel URL
            window.location.href = sessionStorage.getItem('cancel_url');
	}
    }).render("#paypal-button-container"); 

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
	const cookies = document.cookie.split(';');
	for (let i = 0; i < cookies.length; i++) {
	    const cookie = cookies[i].trim();
	    if (cookie.substring(0, name.length + 1) === (name + '=')) {
		cookieValue = decodeURIComponent(cookie.substring(name.length +1));
		break;
	    }
	}
    }
    return cookieValue;
}
