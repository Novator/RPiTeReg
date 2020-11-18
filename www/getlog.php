<?php
// Read GET parameters
$size = $_GET['size'];
if (! $size)
  $size = 20;
$tail = $_GET['tail'];
if (! $tail)
  $tail = $size;
$logind = $_GET['ind'];
if ((! $logind) or ($logind != '2'))
  $logind = '1';

$fn = '/var/www/html/rpitereg'.$logind.'.log';

// Calc number of lines
$count = 0;
$file = fopen($fn, 'r');
while (! feof($file)) {
  $str = fgets($file);
  // $text .= $str;
  $count++;
}
fclose($file);

// Set interval parameters
$start = $count-$tail;
if ($start<1)
  $start = 1;
$end = $start+$size-1;
if ($end>$count)
  $end = $count;

// Seek start line and read lines
$text = '';
$line = 0;
$file = fopen($fn, 'r');
while ((! feof($file)) and ($line<$end)) {
  $line++;
  $str = fgets($file);
  if ($line>=$start)
    $text .= $str;
}
fclose($file);

if (strlen($text)>0)
  echo '===='.$logind.':'.$start.'-'.$end."====\n".$text;
?>