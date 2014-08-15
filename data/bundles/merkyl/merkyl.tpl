<!doctype html>
<html>
<head>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
<script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
<link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
<link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap-theme.min.css">
</head>
<body role="document">


<!-- Fixed navbar -->
    <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="/gui/#">Merkyl</a>
        </div>
        <div class="navbar-collapse collapse">
          <ul class="nav navbar-nav">
            <li class="active"><a href="/gui/">Home</a></li>
            <li><a href="http://github.com/psav/merkyl">About</a></li>
            <!--<li class="dropdown">
              <a href="#" class="dropdown-toggle" data-toggle="dropdown">Server Actions <b class="caret"></b></a>
              <ul class="dropdown-menu">
                <li><a href="/gui/?opo=stopall">Stop All</a></li>
                <li><a href="/gui/?opo=resetall">Reset All</a></li>
                <li><a href="/gui/?opo=deleteall">Delete All</a></li>
                <li class="divider"></li>
                <li class="dropdown-header">System</li>
                <li><a href="/gui/?opo=quit">Quit</a></li>
              </ul>
            </li>-->
          </ul>
        </div><!--/.nav-collapse -->
      </div>
    </div>

    <div class="container theme-showcase" role="main">

      <!-- Main jumbotron for a primary marketing message or call to action -->
      <div class="jumbotron">
        <h2>Merkyl</h2>
          <form method="POST" action="/gui/">
    <input name="filename">
    <button type="submit" name="op" value="add">Add log file</button>
  </form><br>
 % if logs:
<table class="table table-striped">
<tr><td>Logger name</td><td>Temp file name</td><td>Size</td><td>Real Path</td><td>Running</td><td>Operations</td></tr>
   % for log in logs:
   <tr>
     <td>{{log['name']}}</td>
     <td>{{log['tmp_name']}}</td>
     <td>{{log['size']}}</td>
     <td>{{log['filename']}}</td>
     <td>{{log['running']}}</td>
     <td>
       <form action="/gui/" method="POST">
	   <input type="hidden" name="name" value="{{log['name']}}"/>
       % if not log['running']:


	   <button type="submit" class="btn btn-success btn-xs" name="op" value="start">Start</button>
       % else:
	   <button type="submit" class="btn btn-warning btn-xs" name="op" value="reset">Reset</button>
	   <button type="submit" class="btn btn-danger btn-xs" name="op" value="stop">Stop</button>
       % end
	   <button type="submit" class="btn btn-danger btn-xs" name="op" value="delete">Delete</button>
	   <button type="submit" class="btn btn-info btn-xs" name="op" value="view">View</button>
	   <button type="submit" class="btn btn-primary btn-xs" name="op" value="raw">Raw</button>
	 </form>
     </td>
   <tr>
   % end
</table>
<form action="/gui/" method="POST">
  <button type="submit" class="btn btn-success btn-xs" name="op" value="refresh">Refresh</button>
  <button type="submit" class="btn btn-warning btn-xs" name="op" value="resetall">Reset All</button>
  <button type="submit" class="btn btn-danger btn-xs" name="op" value="stopall">Stop All</button>
  <button type="submit" class="btn btn-danger btn-xs" name="op" value="deleteall">Delete All</button>
  <button type="submit" class="btn btn-danger btn-xs" name="op" value="quit" title="Kill Merkyl? (Say it ain't so!)">Kill Merkyl?</button>
</form>
 % elif file_data:
  <pre>{{file_data}}</pre>
 % else:
  <h3> We ain't tailin' anything yet cap'n!
<form action="/gui/" method="POST">
	   <button type="submit" class="btn btn-danger btn-xs" name="op" value="quit" title="Kill Merkyl? (Say it ain't so!)">Kill Merkyl?</button>
</form>
 % end
      </div>





    </div> <!-- /container -->



</body>
</html>
