/**
 * Zenith Healthcare AI Platform - Frontend JavaScript
 * Common utilities and interactions.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});
