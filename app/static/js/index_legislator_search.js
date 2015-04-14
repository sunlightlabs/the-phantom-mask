(function(){

    var classes = {
      'name': [],
      'chamber': {'house':true,'senate':true},
      'state': 'Choose...'
    };

    $('.filter').on('input change',function(evt) {

        $('#filtered').children().each(function(index,ele) {
            $(ele).detach().appendTo($('.pure-g'));
        });

        var $self = $(this);
        if ($self.attr('id') == 'name_search') {
            var val = $(this).val();
            classes['name'] = val == '' ? [] : val.split();
        }

        if ($self.attr('type') == 'checkbox') {
            classes['chamber'][$self.attr('name').replace('_search','')] =  $self.prop('checked');
        }

        if ($self.attr('id') == 'state_search') {
            classes['state'] = $self.val();
        }

        var query = '';
        for (var i=0; i<classes['name'].length; i++) {
            query += '.' + classes['name'][i].toLowerCase().replace(/[^a-z]/g,'');
        }

        if (classes['state'] != 'Choose...') {
            query += '.' + classes['state']
        }

        var query2 = ''; if (classes['chamber']['house']) { query2 = query + '.house'; }
        var query3 = ''; if (classes['chamber']['senate']) { query3 = query + '.senate'; }
        if (query2 != '' || query3 != '') { query = ((query2 != '') ? query2 + ',' : '') + query3; }

        if (query != '')
        {
            var $query = $(query);
            console.log($query);
            $query.each(function(index, ele){
                $(ele).detach().appendTo($('#filtered'));
            });
        }

    });

})();