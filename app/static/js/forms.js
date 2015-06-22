$(document).ready(function () {

    // Remove gray placeholder appearance from select
    $('.form__select').on('change', function() {
        $(this).removeClass('is-gray');
    });

    // Toggle checkbox when repbox is clicked
    $('.repcard').on('click', function(e) {
        $(this).toggleClass('is-selected');
        $(this).find('.repcard__checkbox').each(function() {
            var checkbox = $(this);
            checkbox.prop("checked", !checkbox.prop("checked"));
        });

    });

    // Prevent default checkbox from firing
    $('.repcard__checkbox').click(function(e) {
        e.stopPropagation();
        $(this).parents('.repcard').toggleClass('is-selected');
    });

});