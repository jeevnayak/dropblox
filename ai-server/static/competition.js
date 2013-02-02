var competition = {
  boards: {},
  round: undefined,

  initialize: function() {
    setInterval(function() {
      competition.update();
    }, 1000);
  },

  create_board: function(target, id, header) {
    var html = (
      '<div class="container">' +
      '  <div class="header">' + header + '</div>' +
      '  <object id="' + id + '" data="Board.swf" type="application/x-shockwave-flash" width="175" height="260">' +
      '    <param name="movie" value="Board.swf" />' +
      '    <param name="flashVars" value="squareWidth=10" />' +
      '  </object>' +
      '</div>'
    );
    $('#' + target).append(html);
    return board.initialize(id);
  },

  update: function() {
    competition.post('/competition_state',
      {
        team_name: $.cookie('team_name'),
        password: $.cookie('password'),
      },
      function(data) {
        if (competition.round === undefined) {
          competition.round = data.round;
          $('#round-text').html('Round ' + data.round);
        } else if (competition.round != data.round) {
          return;
        }

        if (data.waiting_for_players) {
          plural = (data.waiting_for_players == 1 ? ' player...' : ' players...');
          $('#login-status').html('Waiting for ' + data.waiting_for_players + plural);
        } else if (data.started) {
          $('#login-status').html('Competition started!');
        } else {
          $('#login-status').html('Ready to start!');
        }

        for (var team in data.boards) {
          if (!competition.boards.hasOwnProperty(team)) {
            $('#boards').append('<div id="' + team + '-container"></div>');
            competition.boards[team] = competition.create_board(team + '-container', team, team);
          } else {
            var board_json = JSON.stringify(data.boards[team]);
            competition.boards[team].setBoardState(board_json);
          }
        }
        for (var team in competition.boards) {
          if (!data.boards.hasOwnProperty(team)) {
            $('#' + team + '-container').remove();
            delete competition.boards[team];
          }
        }
      }
    );
  },

  post: function(url, data, success, error) {
    $.ajax({
      type: 'POST',
      url: url,
      data: JSON.stringify(data),
      contentType: "application/json",
      dataType: "json",
      success: success,
      error: error,
    });
  },
};
