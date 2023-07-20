function Search() {
    var input, filter, table, tr, td, i, txtValue;
    input = document.getElementById("Searchinput");
    filter = input.value.toUpperCase();
    table = document.getElementById("SavedTable");
    tr = table.getElementsByTagName("tr");
    for (i = 0; i < tr.length; i++) {
      td = tr[i].getElementsByTagName("td")[0];
      if (td) {
        txtValue = td.textContent || td.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
          tr[i].style.display = "";
          document.getElementById("msg").style.display = "none";

        } else {
          tr[i].style.display = "none";
          document.getElementById("msg").style.display = "block";


        }
      }
    }
  }

 