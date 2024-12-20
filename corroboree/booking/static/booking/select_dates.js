document.addEventListener('DOMContentLoaded', function() {
		  var arrivalDateInput = document.getElementById('id_arrival_date');
		  var departureDateInput = document.getElementById('id_departure_date');

		  // Set the date picker to highlight the day after arrival date
		  departureDateInput.addEventListener('focus', function() {
		      var arrivalDate = new Date(arrivalDateInput.value);
		      if (arrivalDateInput.value) {
			  arrivalDate.setDate(arrivalDate.getDate() + 1);
			  this.value = arrivalDate.toISOString().split('T')[0];
		      } else {
			  this.removeAttribute('value'); // Do not set value if arrival date is not selected
		      }
		  });

		  departureDateInput.addEventListener('blur', function() {
		      if (!this.value) {
			  this.removeAttribute('value'); // Clear the value after user interaction
		      }
		  });
	      });