(function(){
    $(document).ready(function () {
        try {

            $('#message-form').submit(function(event) {
                var checked = true;
                $('input[type="checkbox"]').each(function(index, value) {
                    if (!$(value).is(':checked')) {
                        checked = false;
                    }
                });
                if (!checked) {
                    // do something
                    event.preventDefault();
                }
            });

            // Remove gray placeholder appearance from select
            $('.form__select').on('change', function () {
                $(this).removeClass('is-gray');
            });

            // Toggle checkbox when repcard is clicked
            $('.repcard').on('click', function (e) {
                $(this).toggleClass('is-selected');
                $(this).find('.repcard__checkbox').each(function () {
                    var checkbox = $(this);
                    checkbox.prop("checked", !checkbox.prop("checked"));
                });

            });

            // Toggle repcard when checkbox is clicked
            $('.repcard__checkbox').click(function (e) {
                e.stopPropagation();
                $(this).parents('.repcard').toggleClass('is-selected');
            });
        } catch(errors) {}
    });
})();

