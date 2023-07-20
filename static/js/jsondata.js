function Jsonexport() {
  var l = document.createElement("a");
  l.href = "data:text/json;charset=UTF-8," + JSON.stringify(document.getElementById("savetxt").innerHTML);
  l.setAttribute("download", `${document.getElementById("dload-fn").value}.json`);
  l.click();
}


function exportData(){
  var table = document.getElementById("tableview");
  var rows =[];
  for(var i=0,row; row = table.rows[i];i++){
      column1 = row.cells[0].innerText;
      column2 = row.cells[1].innerText;
      column3 = row.cells[2].innerText;
      column4 = row.cells[3].innerText;
      column5 = row.cells[4].innerText;
      column6 = row.cells[5].innerText;
      rows.push(
          [
              column1,
              column2,
              column3,
              column4,
              column5,
              column6
          ]
      );

      }
      csvContent = "data:text/csv;charset=utf-8,";
      rows.forEach(function(rowArray){
          row = rowArray.join(",");
          csvContent += row + "\r\n";
      });

      var encodedUri = encodeURI(csvContent);
      var link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", document.getElementById("dload-fn").value);
      document.body.appendChild(link);
      link.click();
}

