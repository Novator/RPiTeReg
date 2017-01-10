<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-str
ict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="ru" xml:lang="ru" dir="ltr">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="locale" content="ru" />
  <title>RPiTeReg control</title>
  <link rev="made" href="mailto:robux@mail.ru" />
  <link rel="shortcut icon" href="favicon.ico" />
  <script>
    var tail = 0;
    var size = 20;
    var req;
    function getData() {
      req = new XMLHttpRequest();
      if (req) {
        tail += size;
        ind = document.getElementById('logind').value;
        req.open("GET", './getlog.php?tail='+tail+'&size='+size+'&ind='+ind, true);
        req.onreadystatechange = processReqChange;
        req.send(null);
      }
    }

    function processReqChange() {
      if (req.readyState == 4) {
        if (req.status == 200) {
          text = req.responseText
          ta = document.getElementById('logtext');
          ta.value = text + ta.value;
        } else {
          alert("Не удалось получить данные:\n"+req.statusText);
        }
      }
    }
  </script>
</head>
<body>
<?php
  $logind = '1';
  $mt1 = filemtime('/var/www/html/rpitereg1.log');
  $mt2 = filemtime('/var/www/html/rpitereg2.log');
  if (($mt2) and (($mt1) and ($mt2>$mt1) or (! $mt1)))
    $logind = '2';
  $ini_fn = '/var/www/html/rpitereg.ini';
  $temp = 23;
  $conf = parse_ini_file($ini_fn, true);
  if ($conf)
    $temp = $conf['common']['aim_temp'];
  if (isset($_POST['submit'])) {
    $new_temp = $_POST['temp'];
    if ($new_temp != $temp) {
      $file = file_get_contents($ini_fn);
      $new_set = 'aim_temp='.$new_temp;
      $file = str_replace('aim_temp='.$temp, $new_set, $file);
      file_put_contents($ini_fn, $file);
      echo '<b>Ini-file ['.$ini_fn.'] changed ('.$new_set.')</b><br />';
      $temp = $new_temp;
    }
  }
  if (isset($_POST['logind']))
    $logind = $_POST['logind'];
?>
  <form action="" method="post">
  Temperature: <input type="text" name="temp" size="5" maxlength="4"
  value="<?php echo $temp; ?>"><input type="submit" name="submit" value="set">
  LogInd: <input type="text" name="logind" id="logind" size="2" maxlength="1" value="<?php echo $logind; ?>">
  </form>
  Last log file lines: <input type="button" value="more..." onClick="getData()"><br />
  <textarea id="logtext" rows="22" cols="90" wrap="off" readonly></textarea>
  <script>
    getData();
  </script>
</body>
</html>

