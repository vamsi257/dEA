document.getElementById("button-convert").disabled= true;
       
$("#convertbutton").on('change', function(){
  document.getElementById("button-convert").disabled= false;
});

$("#selectoption").on('change', function(){
  let op=document.getElementById("selectoption").value;
 
  if (op==1){
    document.getElementById("note").innerText="";
    document.getElementById("jsonfile").style.display="none";
    document.getElementById("button-convert").disabled= false;
  }
  else if (op==2){
    
    document.getElementById("note").innerText="need to upload cloud vision json file";
    document.getElementById("jsonfile").style.display="block";
    document.getElementById("button-convert").disabled= true;
    
    
  }
});
function filestatus(){
    document.getElementById("button-convert").disabled= false;    
}

function convert(){
//alert("file downloaded!");
document.getElementById('hide').style.display="block";
setInterval(function () {document.getElementById('hide').style.display="none";}, 5000);
}