// Booking modal handling
console.log('Hotel management app loaded');

document.addEventListener('DOMContentLoaded', function(){
	const bookingModalEl = document.getElementById('bookingModal');
	if (!bookingModalEl) return;
	const bookingModal = new bootstrap.Modal(bookingModalEl);

	document.querySelectorAll('.book-btn').forEach(btn => {
		btn.addEventListener('click', (e) => {
			const roomId = btn.getAttribute('data-room-id');
			const roomNumber = btn.getAttribute('data-room-number');
			const modalRoomId = document.getElementById('modalRoomId');
			const modalRoomNumber = document.getElementById('modalRoomNumber');
			if (modalRoomId) modalRoomId.value = roomId;
			if (modalRoomNumber) modalRoomNumber.textContent = `#${roomNumber}`;
			bookingModal.show();
		});
	});
  
	// Validate booking form before submit
	const bookingForm = document.getElementById('bookingForm');
	const bookingError = document.getElementById('bookingError');
	if (bookingForm) {
		bookingForm.addEventListener('submit', function(e){
			// perform client-side checks
			const checkin = bookingForm.querySelector('input[name="checkin"]').value;
			const checkout = bookingForm.querySelector('input[name="checkout"]').value;
			const name = bookingForm.querySelector('input[name="name"]').value.trim();
			const today = new Date();
			today.setHours(0,0,0,0);
			let err = '';
			if (!name) err = 'Please enter your name.';
			if (!err && (!checkin || !checkout)) err = 'Please select check-in and check-out dates.';
			if (!err) {
				const ci = new Date(checkin);
				const co = new Date(checkout);
				if (ci < today) err = 'Check-in date cannot be in the past.';
				else if (co <= ci) err = 'Check-out must be after check-in.';
			}
			if (err) {
				e.preventDefault();
				if (bookingError) {
					bookingError.style.display = 'block';
					bookingError.textContent = err;
				} else {
					alert(err);
				}
				return false;
			}
			// allow submit; server will flash a success message which the page renders as a toast
		});
	}

	// Show flashed toasts (if any were rendered server-side)
	document.querySelectorAll('.toast').forEach(function(toastEl){
		try{
			const t = new bootstrap.Toast(toastEl, { delay: 3500, autohide: true });
			t.show();
		}catch(err){
			console.warn('toast show failed', err);
		}
	});
});
