(function(){

    // JQUERY SELECTORS
    var $zip5 = $('#zip5');
    var $city = $('#city');
    var $state = $('#state');
    var $street_address = $('#street_address');
    var $phone_number = $('#phone_number');
    var $no_zip4_error = $('#no-zip4-error');
    var $no_district_error = $('#no-district-error');

    {
        ($zip5.val().length > 0) ? zipcode_css_switch(true) : $zip5.inputmask("99999");
        $phone_number.inputmask('(999) 999-9999');
        create_question_icon($street_address);
        create_question_icon($phone_number);
        $('#street_address_explainer_modal').modal('hide');
        $('#phone_number_explainer_modal').modal('hide');
    }

    function create_question_icon(selector)
    {
        var id = selector.attr('id') + '_explainer';
        var $newEle = $('<img id="'+id+'"width=40 src="/static/images/question_mark_circle.png" style="position:absolute;" />');
        selector.parent().append($newEle);
        var offset = selector.offset();
        offset.left = offset.left - 45;
        $newEle.offset(offset);
        $newEle.click(function(evt) {
            $('#'+id+'_modal').modal('show');
        });
    }

    function zipcode_css_switch(show)
    {
        if (show) {
            $zip5.inputmask("99999-9999");
            $zip5.parent().switchClass('col-sm-12', 'col-sm-3');
            $city.show('slide', {'direction': 'left'});
            $state.show('slide', {'direction': 'left'});
            $no_zip4_error.hide();
            $no_district_error.hide()
        } else {
            $zip5.parent().switchClass('col-sm-3', 'col-sm-12');
            $city.hide(); $state.hide();
            $zip5.inputmask("99999");
            $no_zip4_error.hide();
        }

    }

    function autocomplete_address_values(city, state, zip4, zip5) {
        zipcode_css_switch(true);
        $city.val(city); $state.val(state); $zip5.val(zip5 + zip4);
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

})();