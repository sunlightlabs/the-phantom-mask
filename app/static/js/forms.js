(function(){
    $(document).ready(function () {
        try {
            $(".button__primary[type='submit']").click(function(event) {
                var checked = false;
                $('input[type="checkbox"]').each(function(index, value) {
                    if ($(value).prop('checked')) {
                        checked = true;
                    }
                });
                if (!checked) {
                    event.preventDefault();
                }
            });

            // Remove gray placeholder appearance from select
            $('.form__select').on('change', function () {
                $(this).removeClass('is-gray');
            });

            function checkSubmitButton()
            {
                var checked = false;
                $('input[type="checkbox"]').each(function(index, value) {
                    if ($(value).prop('checked')) {
                        checked = true;
                    }
                });

                if (!checked) {
                    $("button[value='send']").addClass('is-disabled');
                }
                else {
                    $("button[value='send']").removeClass('is-disabled');
                }
            }

            checkSubmitButton();

            // Toggle checkbox when repcard is clicked
            $('.repcard').on('click', function (e) {
                $(this).toggleClass('is-selected');
                $(this).find('.repcard__checkbox').each(function () {
                    var checkbox = $(this);
                    checkbox.prop("checked", !checkbox.prop("checked"));
                });
                checkSubmitButton();
            });

            // Toggle repcard when checkbox is clicked
            $('.repcard__checkbox').click(function (e) {
                e.stopPropagation();
                $(this).parents('.repcard').toggleClass('is-selected');
                checkSubmitButton();
            });
        } catch(errors) {}
    });
})();

