(function(){

    // JQUERY SELECTORS
    var $zip5 = $('#zip5');
    var $city = $('#city');
    var $zip4 = $('#zip4');
    var $state = $('#state');
    var $street_address = $('#street_address');

    function zipcode_css_switch(show)
    {
        if (show) {
            $zip5.parent().switchClass('col-sm-12', 'col-sm-3');
            $city.show('slide', {'direction': 'left'});
            $zip4.show('slide', {'direction': 'left'});
            $state.show('slide', {'direction': 'right'});
            $('#no-zip4-error').hide();
        } else {
            $zip5.parent().switchClass('col-sm-3', 'col-sm-12');
            $city.hide(); $zip4.hide(); $state.hide();
            $('#no-zip4-error').hide();
        }

    }

    function autocomplete_address_values(city, state, zip4, zip5) {
        $city.val(city); $state.val(state); $zip4.val(zip4); $zip5.val(zip5);
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
                    $('#no-zip4-error').show();
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
            if ($zip5.val().length == 5 && $street_address.val().length > 0) {
                autocomplete_address($street_address.val(), $zip5.val());
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