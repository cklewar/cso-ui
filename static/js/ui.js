var grid;
var imageFileName;
var t_deploy_status;

$( document ).ready(function() {
    console.log( "ready function in ui.js" );
    initGrid();

    var wsurl = ws_client_protocol + "://" + ws_client_ip + ":" + ws_client_port + "/ws?clientname=" + clientname;
    var ws;
    console.log(wsurl);

    if (window.WebSocket) {
        ws = new WebSocket(wsurl, "cso_ui");
      }
      else if (window.MozWebSocket) {
        ws = MozWebSocket(wsurl);
      }
      else {
        console.log('WebSocket Not Supported');
        return;
      }

    var $message = $('#message');

    ws.onopen = function(){

      $message.attr("class", 'label label-success');
      $message.text('open');

    };

    ws.onmessage = function(ev){

        var json = JSON.parse(ev.data);
        console.log(json);

        if (json.action === 'v2_playbook_on_play_start'){

            if (json.targets) {

                rowNode = t_deploy_status.row.add( {
                    "target":   json.target,
                    "task":   json.task,
                    "status": json.status,
                } ).draw().node()

                $(rowNode).attr("id", json.target + '_' + json.uuid);

                $( rowNode )
                .css( 'color', 'black' )
                .css( 'background-color', '#b7b7b7')
                .animate( { color: 'black' } );

                $.each( json.targets, function( target, uuid ) {

                    rowNode = t_deploy_status.row.add( {
                        "target":   target,
                        "task":   json.task,
                        "status": json.status,
                    } ).draw().node()

                    $(rowNode).attr("id", target + '_' + uuid);
                    $( rowNode )
                    .css( 'color', 'black' )
                    .css( 'background-color', '#d6d6d6')
                    .animate( { color: 'black' } );
                });

            } else {

                rowNode = t_deploy_status.row.add( {
                    "target":   json.target,
                    "task":   json.task,
                    "status": json.status,
                } ).draw().node()

                $(rowNode).attr("id", json.target + '_' + json.uuid);

                $( rowNode )
                .css( 'color', 'black' )
                .css( 'background-color', '#b7b7b7')
                .animate( { color: 'black' } );
            }

        } else if (json.action === 'v2_playbook_on_task_start'){

            rowNode = t_deploy_status.row.add(  {
                "target": json.target,
                "task": json.task,
                "status": json.status,
            } ).draw().node();

            $(rowNode).attr("id", json.target + '_' + json.uuid);

            $( rowNode )
            .css( 'color', 'black' )
            .css( 'background-color', '#d6d6d6')
            .animate( { color: 'black' } );

        } else if (json.action === 'v2_runner_on_ok'){
            var temp = t_deploy_status.row('#' + json.target + '_' + json.uuid).data();
            temp.target = json.target;
            temp.status = json.status;
            t_deploy_status.row('#' + json.target + '_' + json.uuid).data(temp).invalidate();

        } else if (json.action === 'v2_runner_on_failed'){
            var temp = t_deploy_status.row('#' + json.target + '_' + json.uuid).data();
            temp.target = json.target;
            temp.status = json.status;
            t_deploy_status.row('#' + json.target + '_' + json.uuid).data(temp).invalidate();

        } else if (json.action === 'v2_play_on_end'){
            var temp = t_deploy_status.row('#' + json.target + '_' + json.uuid).data();
            temp.target = json.target;
            temp.status = json.status;
            t_deploy_status.row('#' + json.target + '_' + json.uuid).data(temp).invalidate();

        } else if (json.action === 'update_session_output'){
            $("#session_output").append(json.msg);
            $('#session_output').trigger("change");

        } else if (json.action === 'add_tasks'){
            t_deploy_status.clear().draw();

            $.each(json.data, function( index, target) {
                $.each(target.tasks, function(k , v) {

                    rowNode = t_deploy_status.row.add(  {
                        "target": target.name,
                        "task": v.name,
                        "status": v.status ,
                    }).draw().node();
                    $(rowNode).attr("id", v.uuid);
                });

            });
        } else if (json.action === 'update_task_status') {

            var temp = t_deploy_status.row('#' + json.uuid).data();
            temp.status = json.status;
            t_deploy_status.row('#' + json.uuid).data(temp).invalidate();
        }
    };

    ws.onclose = function(ev){

      $message.attr("class", 'label label-important');
      $message.text('closed');
    };

    ws.onerror = function(ev){

      $message.attr("class", 'label label-warning');
      $message.text('error occurred');
    };

    t_deploy_status = $('#t_deploy_status').DataTable({
        "columns": [
            {
                "data": "target",
                "defaultContent": ""
            },
            {
                "data": "task",
                "defaultContent": ""
            },
            {
                "data": "status",
                "defaultContent": ""
            },
        ],
        "info": false,
        "ordering": false,
        "paging": false,
        "scrollY": "350px",
        "scrollCollapse": true
    });


    $('#btnCardAdd').on('click', function (event) {
        var cardData = $("#formAddCard").serializeArray();
        addCard(cardData);
    });

    $('.btnCardDelete').on('click', function (event) {
        deleteCard($(this).data('source'));
    });

    $("#formSaveCardSettings").submit(function(event) {
        event.preventDefault();

        var $form = $( this ),
          cardId = $form.attr('action');
          title = $form.find('input[name="title"]').val(),
          playbook = $form.find('input[name="playbook"]').val(),
          directory = $form.find('input[name="directory"]').val(),
          description = $form.find('textarea[name="description"]').val();

        var cardData = {"cardId": cardId, "title": title, "playbook": playbook, "directory": directory, "description": description}

        $.ajax({
            url: '/api/cards?action=save',
            type: 'POST',
            data: JSON.stringify(cardData),
            cache: false,
            dataType: 'json',
            contentType: 'application/json',
            success: function (response) {
                console.log(response);
                $('#cardSettingsModal_' + cardId).modal('hide');
            },
            error : function (data, errorText) {
                $("#errormsg").html(errorText).show();
            }
        });
    });

    $('.btnDeployUseCase').on('click', function (event) {
        var data = {};
        data.use_case_name = ($(this).data('usecase'));
        deploy(data);
    });

    $('#modalDeployStatus').on('shown.bs.modal', function (e) {
        t_deploy_status.clear();
        t_deploy_status.columns.adjust();
        $("#session_output").val('');
        $('#session_output').trigger("change");

    });

    $(function () {
        $('#cardImageFile').fileupload({
            url: '/api/upload',
            type: 'POST',
            dataType: 'json',
            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $("#dynamic")
                    .css("width", progress + "%")
                    .attr("aria-valuenow", progress)
                    .text(progress + "% Complete");

            },
            done: function (e, data) {
                imageFileName = data.files[0].name;
            }
        });
    });

    $("#session_output").on('change', function(){
        scrollToBottom();
    });
});

function scrollToBottom() {
  $('#session_output').scrollTop($('#session_output')[0].scrollHeight);
}


function initGrid() {
  grid = new Muuri('.grid', {
    dragEnabled: true,
    layoutOnInit: false
  }).on('move', function () {
    saveLayout(grid);
  });

  var layout = window.localStorage.getItem('layout');
  if (layout) {
    loadLayout(grid, layout);
  } else {
    grid.layout(true);
  }
}

function serializeLayout(grid) {
  var itemIds = grid.getItems().map(function (item) {
    return item.getElement().getAttribute('data-id');
  });
  return JSON.stringify(itemIds);
}

function saveLayout(grid) {
  var layout = serializeLayout(grid);
  window.localStorage.setItem('layout', layout);
}

function loadLayout(grid, serializedLayout) {
  var layout = JSON.parse(serializedLayout);
  var currentItems = grid.getItems();
  var currentItemIds = currentItems.map(function (item) {
    return item.getElement().getAttribute('data-id')
  });
  var newItems = [];
  var itemId;
  var itemIndex;

  for (var i = 0; i < layout.length; i++) {
    itemId = layout[i];
    itemIndex = currentItemIds.indexOf(itemId);
    if (itemIndex > -1) {
      newItems.push(currentItems[itemIndex])
    }
  }

  grid.sort(newItems, {layout: 'instant'});
}

function addCard(cardData){

    cardData.push({'name': 'image', 'value': imageFileName});

    $.ajax({
        url: '/api/cards?action=add',
        type: 'POST',
        data: JSON.stringify(cardData),
        cache: false,
        dataType: 'json',
        contentType: 'application/json',
        success: function (response) {
            grid.add($.parseHTML( response ));
            $('#modalAddCard').modal('hide');
        },
        error : function (data, errorText) {
            $("#errormsg").html(errorText).show();
        }
    });
}

function deleteCard(cardData){

    $.ajax({
        url: '/api/cards?action=delete',
        type: 'POST',
        data: JSON.stringify(cardData),
        cache: false,
        processData: true,
        dataType: 'json',
        contentType: 'application/json',
        success: function (response) {
            var item = [$("#" + cardData)[0]];
            grid.remove(grid.getItems(item)[0], {removeElements: true});
        },
        error : function (data, errorText) {
            $("#errormsg").html(errorText).show();
        }
    });
}

function deploy(data){

    data.action = 'fetch';

    $.ajax({
        url: '/api/deploy',
        type: 'POST',
        data: JSON.stringify(data),
        cache: false,
        processData: true,
        dataType: 'json',
        contentType: 'application/json',
        success: function (response) {
            //$("#loader").hide();
            console.log(response);
            //var tmp = t_deploy_status.row('#' response.uuid).data();
            //tmp.status = response.result;
            //t_deploy_status.row('#' + response.target + '_' + response.uuid).data(tmp).invalidate();

            if (response.result === 'OK') {
                data.action = 'run';

                $.ajax({
                    url: '/api/deploy',
                    type: 'POST',
                    data: JSON.stringify(data),
                    cache: false,
                    processData: true,
                    dataType: 'json',
                    contentType: 'application/json',
                    success: function (response) {
                        //$("#loader").hide();
                        console.log(response);
                        //var tmp = t_deploy_status.row('#' + response.target + '_' + response.uuid).data();
                        //tmp.status = response.result;
                        //t_deploy_status.row('#' + response.target + '_' + response.uuid).data(tmp).invalidate();
                    },
                    error : function (data, errorText) {
                        $("#errormsg").html(errorText).show();
                    }
                });
            }
        },
        error : function (data, errorText) {
            $("#errormsg").html(errorText).show();
        }
    });
}


