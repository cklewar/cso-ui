var grid;
var imageFileName;
var t_deploy_status;
var isDeploying = false;
var ws = null;
var isDeployed = true;

$( document ).ready(function() {
    console.log( "ready function in ui.js" );
    initGrid();

    var wsurl = ws_client_protocol + "://" + ws_client_ip + ":" + ws_client_port + "/ws?clientname=" + clientname;
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

    ws.onopen = function(){
      console.log('Websocket connection opened');
      heartbeat();
    };

    ws.onmessage = function(ev){

        var json = JSON.parse(ev.data);
        //console.log(json);

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

            $("#session_output_" + json.task + "_" + json.uuid.replace(/\-/g, '_')).append(json.msg + '\n');
            $('#session_output_' + json.task + '_' + json.uuid.replace(/\-/g, '_')).trigger("change");

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

            var temp = t_deploy_status.row('#' + json.task + '_' + json.uuid).data();
            temp.status = json.status;
            t_deploy_status.row('#' + json.task + '_' + json.uuid).data(temp).invalidate();

            if (json.status === 'Done') {
                var row = t_deploy_status.row('#' + json.task + '_' + json.uuid).node();
                $('td', row).eq(2).css('color', 'green');

            } else {
                var row = t_deploy_status.row('#' + json.task + '_' + json.uuid).node();
                $('td', row).eq(2).css('color', 'black');
            }

        } else if (json.action === 'update_card_deploy_status'){

            if (lastDeployedUseCase !== json.usecase){
                $('#' + lastDeployedUseCase + ' > div > div').removeClass("deployed");
                //$('#' + lastDeployedUseCase + ' > div > div > img').attr("src", "/static/images/dummy.png");
                $('#' + json.usecase + ' > div > div').addClass("deployed");
                $('#' + json.usecase + ' > div > div > img').attr("src", "/static/images/" + json.image);
                isDeploying = false;
                lastDeployedUseCase = json.usecase;

            } else {
                lastDeployedUseCase = json.usecase;
            }
        } else {
            console.log(json);
        }
    };

    ws.onclose = function(ev){
      console.log('Websocket connection closed');
      alert("Websocket connection closed. Refresh browser session");
    };

    ws.onerror = function(ev){
      alert("Websocket connection failed: " + ev.type);
    };

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
                $('#cardSettingsModal_' + cardId).modal('hide');
            },
            error : function (data, errorText) {
                $("#errormsg").html(errorText).show();
            }
        });
    });

    $('.btnDeployUseCase').on('click', function (event) {
        var data = {};
        data.use_case_name = $(this).data('usecase');

        //if ($("#" + data.use_case_name + ' > div > div').hasClass("deployed")) {
        //   console.log('Already deployed should we re-deploy?');
        //   isDeploying = false;

        //} else {
        //    isDeploying = true;
        //    $('#modalDeployStatus').modal('toggle');
        //    deploy(data);
        //}
        //$( "body" ).data( "foo", 52 );
        //('#mydiv').data('myval',20);
        $("#modalDeployStatus").data("usecase", data.use_case_name);
        deploy(data);

    });

    $('#modalDeployStatus').on('hidden.bs.modal', function (e) {
        var modals = $('.modal_task_details_' + $('#modalDeployStatus').data('usecase'));
        $.each(modals, function( index, modal ) {
            modal.remove();
        });
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

    $('#img_poc_ref').zoom({magnify: 1});

    $('.card-img-top').on('click', function(e){
        $("#caption").text($(this).attr('alt'));
        $('#modalUseCaseImg').css("display", "block");
        $("#useCaseDetailImg").attr("src", $(this).attr('src'));
        $('.btnCloseUseCaseImgDetail').on('click', function(e){
            $('#modalUseCaseImg').css("display", "none");
        });
    });
});

function heartbeat() {
  if (!ws){
    return;
  }
  if (ws.readyState !== 1) {
    return;
  }
  ws.send(JSON.stringify({ message: "heartbeat" }));
  setTimeout(heartbeat, 5000);
}

function scrollToBottom(elem) {
    elem.scrollTop( elem.prop("scrollHeight"));
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

    if ($.fn.DataTable.isDataTable("#t_deploy_status")) {
        $('#t_deploy_status').DataTable().clear().destroy();
    }

    data.action = 'clone';

    $.ajax({
        url: '/api/deploy',
        type: 'POST',
        data: JSON.stringify(data),
        cache: false,
        processData: true,
        dataType: 'json',
        contentType: 'application/json',
        beforeSend: function() {
            $("#divSpinner").show();
        },
        success: function (response) {
            $("#divSpinner").hide();

            if (response[0]) {

                $('#modalDeployStatus').modal('toggle');
                isDeploying = true;
                data.action = 'target_tasks';
                t_deploy_status = $('#t_deploy_status').DataTable({
                    'ajax'       : {
                        "type"   : "POST",
                        "url"    : "/api/deploy",
                        "data": function ( d ) {
                            return JSON.stringify( data );
                        },
                        "contentType": "application/json",
                        "processData": true,
                        "dataType": "json",
                        "destroy": true,
                        "dataSrc": function (response) {
                            var return_data = new Array();
                            var modal_task_details;

                            $.each(response[1], function( data ) {
                                var target = this;
                                $.each(target.tasks, function( index, task ) {
                                    return_data.push({
                                        'target': target.name,
                                        'task':  task.name,
                                        'status': task.status,
                                        'uuid': target.uuid
                                    });
                                    modal_task_details = '<div class="modal modal_task_details_' + target.usecase + '" id="modalDeployDetail_' + task.name + '_' + target.uuid + '" tabindex="-1" role="dialog" data-backdrop="static" data-keyboard="false">' +
                                    '<div class="modal-dialog modal-lg" role="document">' +
                                        '<div class="modal-content">' +
                                            '<div class="modal-header">' +
                                                '<h5 id="modalDeployStatusTitle" class="modal-title">Task: '+ task.name + ' details' + '</h5>' +
                                                '<button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
                                                    '<span aria-hidden="true">&times;</span>' +
                                                '</button>' +
                                            '</div>' +
                                            '<div class="modal-body h-50">' +
                                                '<div>' +
                                                    '<pre class="session_output" id="session_output_' + task.name + '_' + target.uuid.replace(/\-/g, '_') + '">' +
                                                    '</pre>' +
                                                '</div>' +
                                            '</div>' +
                                            '<div class="modal-footer">' +
                                                '<button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>' +
                                            '</div>' +
                                        '</div>' +
                                    '</div>' +
                                    '</div>';
                                  $("body").append(modal_task_details);
                                  $('#session_output_' + task.name + '_' + target.uuid.replace(/\-/g, '_')).on('change', function(){
                                    scrollToBottom($('#session_output_' + task.name + '_' + target.uuid.replace(/\-/g, '_')));
                                  });
                                });
                            });
                            return return_data;
                        }
                    },
                    "initComplete":function( settings, json){
                        data.action = 'run';
                        console.log('Init complete. Run deployment...');
                        $.ajax({
                            url: '/api/deploy',
                            type: 'POST',
                            data: JSON.stringify(data),
                            cache: false,
                            processData: true,
                            dataType: 'json',
                            contentType: 'application/json',
                            success: function (response) {

                            },
                            error : function (data, errorText) {
                                $("#errormsg").html(errorText).show();
                            }
                        });
                    },
                    "createdRow": function( row, data, dataIndex ) {
                        $(row).attr('id', data.task + '_' + data.uuid);
                    },
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
                            "defaultContent": "",
                            "width": "40%"
                        },
                    ],
                    "info": false,
                    "ordering": false,
                    "paging": false,
                    "scrollY": "350px",
                    "scrollCollapse": true
                });
            } else {
                $('#modalMessage > div > div > div.modal-body.h-50').text(response[1]);
                $('#modalMessage').modal('toggle');
            }
        },
        error : function (data, errorText) {
            $("#errormsg").html(errorText).show();
        },
        complete: function() {
            $("#divSpinner").hide();
        }
    });

    $('#t_deploy_status tbody').on('dblclick', 'tr', function () {
        var data = t_deploy_status.row( this ).data();
        $('#modalDeployDetail_' + data.task + '_' + data.uuid).modal('show');
        scrollToBottom($('#session_output_' + data.task + '_' + data.uuid.replace(/\-/g, '_')));
    });
}