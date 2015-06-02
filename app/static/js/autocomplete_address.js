(function(){

    // JQUERY SELECTORS
    var $zip5 = $('#zip5');
    var $city = $('#city');
    var $state = $('#state');
    var $street_address = $('#street_address');
    var $phone_number = $('#phone_number');
    var $no_zip4_error = $('#no-zip4-error')

    console.log($zip5.val());
    console.log($zip5.val().length);
    if ($zip5.val().length > 5)
    {
        $zip5.inputmask("99999-9999");
        zipcode_css_switch(true);
    }
    else
    {
        $zip5.inputmask("99999");
    }

    $phone_number.inputmask('(999) 999-9999');

    function zipcode_css_switch(show)
    {
        if (show) {
            $zip5.parent().switchClass('col-sm-12', 'col-sm-3');
            $city.show('slide', {'direction': 'left'});
            $state.show('slide', {'direction': 'left'});
            $no_zip4_error.hide();
        } else {
            $zip5.parent().switchClass('col-sm-3', 'col-sm-12');
            $city.hide(); $state.hide();
            $zip5.inputmask("99999");
            $no_zip4_error.hide();
        }

    }

    function autocomplete_address_values(city, state, zip4, zip5) {
        $zip5.inputmask("99999-9999");
        $city.val(city); $state.val(state); $zip5.val(zip5 + zip4);
        zipcode_css_switch(true);
    }

    function autocomplete_address(street_address, zip5) {
        $.ajax({
            type: 'POST',
            url: '/ajax/autofill_address',
            contentType: 'application/json',
            data: JSON.stringify({'street_address': street_address, 'zip5': zip5}),
            dataType: 'json',
            success: function(result) {
                if ('error' in result) {
                    $no_zip4_error.show();
                    $state.val('');
                    $city.val('');
                } else {
                    autocomplete_address_values(result['city'], result['state'], result['zip4'], result['zip5']);
                }
            },
            error: function(xhr, ajaxOptions, thrownError) {

            }
        });
    }

    var options = {
        callback: function (value) {
            var zip5_val = $zip5.val().replace(/\D/g, '');
            if (zip5_val.length == 5 && $street_address.val().length > 0) {
                autocomplete_address($street_address.val(), zip5_val);
            }
        },
        wait: 500,
        highlight: false,
        captureLength: 0
    };

    $zip5.typeWatch( options );
    $street_address.typeWatch( options );

    /*
    $zip5.on('keyup change', function(evt) {
        if ($zip5.val().length == 0) {
            zipcode_css_switch(false);
        } else if ($zip5.val().length == 5 && $street_address.val().length > 0) {
            autocomplete_address($street_address.val(), $zip5.val());
        }
    });
    */




})();