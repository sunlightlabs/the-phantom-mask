(function(){

    /*
    $('.pure-g input').blur(function(evt) {

        var attr_map = {
            'street_address': $('#street_address').val(),
            'city': $('#city').val(),
            'state': $('#state').val()
        };

        for (var key in attr_map) { if (attr_map.hasOwnProperty(key) && attr_map[key] == '') { return } }

        attr_map['zip5'] = $('#zip5').val();



    });
    */

    $.ajax({
        type: 'POST',
        url: '/ajax/autofill_address',
        contentType: 'application/json',
        data: JSON.stringify({'street_address': 'PO Box 1332', 'zip5': '27948'}),
        dataType: 'json',
        success: function(result) {
            console.log(result);
        },
        error: function(xhr, ajaxOptions, thrownError) {

        }
    })

})();