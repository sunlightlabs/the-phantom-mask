$(document).ready(function () {

    // Remove gray placeholder appearance from select

    $('.form__select').on('change', function() {
        $(this).removeClass('is-gray');
    });


    // Toggle checkbox when repbox is clicked

    $('.repcard').on('click', function() {
        $(this).toggleClass('is-selected');

        $(this).find('.repcard__checkbox').each(function() {
            var checkbox = $(this);
            checkbox.prop("checked", !checkbox.prop("checked"));
        });
    });

});