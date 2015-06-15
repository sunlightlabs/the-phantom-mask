$(document).ready(function () {

    // Remove gray placeholder appearance from select

    $('.form__select').on('change', function() {
        $(this).removeClass('is-gray');
    });

});