var grid;
var imageFileName;
var t_deploy_status;

$( document ).ready(function() {
    console.log( "ready function in ui.js" );
    initGrid();

    //var wsurl = scheme + "://" + host + ":" + port + "/yapt/ws?clientname=" + clientname;
    var wsurl =  "ws://127.0.0.1:8080/ws?clientname=" + clientname;
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

            rowNode = t_deploy_status.row.add( {
                "host":   json.host,
                "task":   json.task,
                "status": json.status,
            } ).draw().node()

            $(rowNode).attr("id", json.uuid);

            /*$( rowNode )
            .css( 'color', 'red' )
            .animate( { color: 'black' } );
            */

        } else if (json.action === 'v2_playbook_on_task_start'){

            rowNode = t_deploy_status.row.add(  {
                "host": json.host,
                "task": json.task,
                "status": json.status,
            } ).draw().node();

            $(rowNode).attr("id", json.uuid);

        } else if (json.action === 'v2_runner_on_ok'){

            var temp = t_deploy_status.row('#'+json.uuid).data();
            temp.status = json.status;
            t_deploy_status.row('#'+json.uuid).data(temp).invalidate();

        } else if (json.action === 'v2_runner_on_failed'){

            var temp = t_deploy_status.row('#'+json.uuid).data();
            temp.host = json.host;
            temp.status = json.status;
            t_deploy_status.row('#'+json.uuid).data(temp).invalidate();
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
        "destroy": true,
        "columns": [
            {
                "data": "host",
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
        //"scrollY": "300px",
        //"scrollCollapse": true
    });


    $('#btnCardAdd').on('click', function (event) {
        var cardData = $("#formAddCard").serializeArray();
        addCard(cardData);
    });

    $('.btnCardDelete').on('click', function (event) {
        deleteCard($(this).data('source'));
    });

    $('#btnDeployUseCase').on('click', function (event) {
        console.log('deployUseCase');
        console.log(($(this).data('usecase')));
        var data = {};
        data.use_case_name = ($(this).data('usecase'));
        deploy(data);
    });

    $('#modalDeployStatus').on('shown.bs.modal', function (e) {
        t_deploy_status.columns.adjust();
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
});

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
    console.log(data);

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
            $("#loader").hide();
            console.log(response);
            var tmp = t_deploy_status.row('#'+response.uuid).data();
            tmp.status = response.result;
            t_deploy_status.row('#'+response.uuid).data(tmp).invalidate();

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
                        $("#loader").hide();
                        console.log(response);
                        //var tmp = t_deploy_status.row('#'+response.uuid).data();
                        //tmp.status = response.result;
                        //t_deploy_status.row('#'+response.uuid).data(tmp).invalidate();
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


