(function(){

    $('.pure-g input').blur(function(evt) {

        var attr_map = {
            'street_address': $('#street_address').val(),
            'city': $('#city').val(),
            'state': $('#state').val()
        };

        for (var key in attr_map) { if (attr_map.hasOwnProperty(key) && attr_map[key] == '') { return } }

        attr_map['zip5'] = $('#zip5').val();

        $.ajax({
            method: "GET",
            url: "/contact_congress/zip4_lookup",
            date: attr_map,
            success: function(result) {
                alert (result);
            },
            error: function(xhr, ajaxOptions, thrownError) {

            }
        })

    });

})();