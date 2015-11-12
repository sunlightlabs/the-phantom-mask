(function(){

    function init_autocomplete($form) {
        // JQUERY SELECTORS
        var $submit = $form.find("button[type='submit']");
        var $zip5 = $form.find("[name='zip5']");
        var $city = $form.find("[name='city']");
        var $state = $form.find("[name='state']");
        var $street_address = $form.find("[name='street_address']");
        var $phone_number = $form.find("[name='phone_number']");
        var $no_zip4_error = $form.find('.form__error--zip');
        var $no_district_error = $form.find('.no-district-error');
        var $autofill__group = $form.find('.autofill__group');

        function zipcode_css_switch(show) {
            if (show) {
                $zip5.inputmask("99999-9999", { showMaskOnHover: false });
                $zip5.parent().removeClass('is-fullwidth');

                $city.parent().removeClass('is-hidden').removeClass('is-concealed');
                $state.parent().removeClass('is-hidden').removeClass('is-concealed');

                $no_zip4_error.hide();
                $no_district_error.hide()
            }
        }

        function autocomplete_address_values(city, state, zip4, zip5) {
            zipcode_css_switch(true);
            $city.val(city); $state.val(state); $zip5.val(zip5 + zip4);
            $state.removeClass('is-gray');
        }

        function autocomplete_address(street_address, zip5) {
            $submit.prop('disabled', true);
            $submit.text('Autofilling address ... please wait');
            $.ajax({
                type: 'POST',
                url: URL_PREFIX  + '/ajax/autofill_address',
                contentType: 'application/json',
                data: JSON.stringify({'street_address': street_address, 'zip5': zip5.substring(0,5)}),
                dataType: 'json',
                timeout: 3000,
                success: function(result) {
                    if ('error' in result) {
                        zipcode_css_switch(true);
                        $no_zip4_error.show();
                        $autofill__group.addClass('has-error');
                        $submit.prop('disabled', false);
                        $submit.text('Submit');
                    } else {
                        autocomplete_address_values(result['city'], result['state'], result['zip4'], result['zip5']);
                        $submit.prop('disabled', false);
                        $submit.text('Submit');
                    }
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    if(textStatus==="timeout") {
                        zipcode_css_switch(true);
                        $no_zip4_error.show();
                        $autofill__group.addClass('has-error');
                    }
                },
                complete: function(jqXHR, textStatus) {
                    typeWatch_lock = false;
                }
            });
        }

        var typeWatch_lock = false;
        var options = {
            callback: function (value) {
                var zip5_val = $zip5.val().replace(/\D/g, '');
                if (zip5_val.length == 5 && $street_address.val().length > 0) {
                    if (!typeWatch_lock) {
                        typeWatch_lock = true;
                        autocomplete_address($street_address.val(), zip5_val);
                    }
                }
            },
            wait: 500,
            highlight: false,
            captureLength: 0
        };

        ($zip5.val().length > 0) ? zipcode_css_switch(true) : $zip5.inputmask("99999", {showMaskOnHover: false});
        $phone_number.inputmask('(999) 999-9999', {showMaskOnHover: false});

        $zip5.typeWatch(options);
        $street_address.typeWatch(options);
    }


    $(document).ready(function() {
        try { init_autocomplete($("#lookup-form"))} catch(error) {}
        try { init_autocomplete($("#address-form"))} catch(error) {}
    });

})();