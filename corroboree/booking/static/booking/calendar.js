     document.addEventListener('DOMContentLoaded', function() {
         var calendarEl = document.getElementById('calendar');

	 function fetchRoomAvailability(start, end) {
	     $.ajax({
		 url: '/api/get-room-availability/',
		 data: {
		     start: start,
		     end: end
		 },
		 success: function(data) {
		     var events = [];
		     for (var date in data) {
			 var freeRooms = data[date];
			 var colours = [
			     '#e51f1f',
			     '#f2a134',
			     '#f7e379',
			     '#bbdb44',
			     '#44ce1b',
			 ]
			 var index = Math.ceil(freeRooms.length / 2)
			 var color = colours[index]
			 events.push({
			     title: freeRooms.length + ' room' + (freeRooms.length === 1 ? '' : 's') + ' free',
			     start: date,
			     textColor: 'black',
			     color: color,
			     description: 'Free rooms:\n' + freeRooms.join('\n'),
			     display: 'background',
			 });
		     }
		     calendar.removeAllEvents();
		     calendar.addEventSource(events);
		 }
             });
         }

         var calendar = new FullCalendar.Calendar(calendarEl, {
             initialView: 'dayGridMonth',
	     locale: 'en-AU',
	     selectable: true,
	     datesSet: function(info) {
		 fetchRoomAvailability(info.startStr, info.endStr);
             },
	     select: function(info) {
		 var start = new Date(info.startStr);
		 var end = new Date(info.endStr);

		 if ((end.getTime() - start.getTime()) === 86400000) {
		     // Do not subtract a day if only one day is selected
             end = end.toISOString().split('T')[0];
         } else {
		     // select range is always 1 more, correct that for intuitive behaviour with booking system
		     end.setDate(end.getDate() - 1);
		     end = end.toISOString().split('T')[0];
		 }
		 start = start.toISOString().split('T')[0];
		 window.location.href = `/make-a-booking/?arrival_date=${start}&departure_date=${end}`;
	     },
	     eventDidMount: function(info) {
		 var tooltip = new Tooltip(info.el, {
		     title: info.event.extendedProps.description,
		     placement: 'top',
		     trigger: 'hover',
		     container: 'body',
		 });
             },
         });
	 calendar.render();
     });