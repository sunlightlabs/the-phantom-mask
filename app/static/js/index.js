(function(){
    $(document).ready(function(){
        var $lookup_form = $("#lookup-form");
        $lookup_form.submit(function(event) {
            event.preventDefault();
            $.ajax({
                type: 'POST',
                url: URL_PREFIX + '/',
                data: $(this).serialize() + '&leg_lookup=leg_lookup',
                dataType: 'json',
                timeout: 3000,
                success: function (result) {
                    $('#legislator-display').html($(result['leg_lookup']));
                },
                error: function (jqXHR, textStatus, errorThrown) {

                },
                complete: function (jqXHR, textStatus) {

                }
            });
        })
    });
})();