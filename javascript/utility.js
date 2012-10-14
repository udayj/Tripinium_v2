function search()
{
  var place=document.getElementById("search");
  if(place==null || place.value.trim()=="")
    return;
  window.location="/search?location="+place.value;
}

function toTitleCase(str)
{
    return str.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
}

function print()
{

    var content=document.getElementById("data").innerHTML;
    var place_name=document.getElementById("place_name").innerHTML;
    myWin=window.open('','Tips from Tripinium','menubar,scrollbars,left=30px,top=40px,height=400px,width=600px'); 
    myWin.document.write('<body onload="window.print();">'+place_name+'<br>'+content+'</body>');
    myWin.print();
    myWin.close();
}

function send_feedback(place)
{
    var data=document.getElementById('user_tips').value;
    if(data=="" || data==null)
    {
        alert("No feedback entered !");
        return;
    }
    $.ajax({
  type: "POST",
  url: "/user_tips",
  data: { tip: data,place:place},
  
  success: function(data)
  {

    var display_class=[];
    display_class['Infantry']='badge-infantry';
    display_class['Cavalry']='badge-cavalry';
    display_class['Governor']='badge-governor';
    display_class['Ambassador']='badge-ambassador';
    display_class['Envoy']='badge-envoy';
    display_class['Diplomat']='badge-diplomat';
    display_class['Humming-Bird']='badge-humming-bird';
    display_class['Koel']='badge-koel';
    display_class['Nightingale']='badge-nightingale';
    $('#user_tips').val('');
  if(data['user']=='y')
    {
      $('#reward').html('You earned new badges <span class="badge '+
        display_class[data['badges_earned'][0].substr(data['badges_earned'][0].indexOf(':')+1)]+'">'+data['badges_earned'][0]+'</span>');
      $('#reward').css('display','inline');
      $('#reward').css('margin-top','10px');
    }
    else
    {

      $('#reward').html(data['thanks']);
      $('#reward').css('display','inline');
      $('#reward').addClass('alert').addClass('alert-success');
      $('#reward').css('max-width','180px');
      $('#reward').css('margin-top','');
    }
    $('#milestone').html(data['place_milestone'])
  },
  fail: function()
  {
    
    alert("Problem submitting feedback :(. Thanks anyways");
  }
}).done(function( msg ) {
 // document.getElementById("user_tips").value="";
  //alert("Thanks for helping us improve!");
});
}

function calculateRating()
{
    var total_rating=$('#total_rating').attr('class');
    var total_rating_count=$('#total_rating_count').attr('class');
    
    
    if(total_rating!='None' && total_rating_count!='None')
    {
        return parseFloat(total_rating)/parseInt(total_rating_count);
        

    }
    else
    {
        return 0;
    }
}

function send_email()
{
    var emails=document.getElementById('email_field').value;
    var name=document.getElementById('name_field').value;
    var place=document.getElementById('email_place').innerHTML;
    if(emails=="" || emails==null)
    {
        alert("No email-id entered");
        return;
    }
    $.ajax({
  type: "POST",
  url: "/send_email",
  data: { emails:emails,name:name,place:place},
  
  success: function()
  {
    alert('Your request is being processed. Email would be delivered shortly');
  },
  fail: function()
  {
    
    alert('Problem processing email request. We are looking into this.');
  }
}).done(function( msg ) {
 // document.getElementById("user_tips").value="";
  //alert("Thanks for helping us improve!");
});
}

function send_social_action(action,place)
{
 $.ajax({
  type: "POST",
  url: "/send_social_action",
  data: { action:action,place:place},
  
  success: function(data)
  {
    var display_class=[];
    display_class['Infantry']='badge-infantry';
    display_class['Cavalry']='badge-cavalry';
    display_class['Governor']='badge-governor';
    display_class['Ambassador']='badge-ambassador';
    display_class['Envoy']='badge-envoy';
    display_class['Diplomat']='badge-diplomat';
    display_class['Humming-Bird']='badge-humming-bird';
    display_class['Koel']='badge-koel';
    display_class['Nightingale']='badge-nightingale';

    if(data['user']=='y')
    {
      $('#reward').html('You earned new badges <span class="badge '+display_class[data['badges_earned'][0]]+'">'+data['badges_earned'][0]+'</span>');
      $('#reward').css('display','inline');
      $('#reward').css('margin-top','10px');
    }
    else
    {
      $('#reward').html(data['thanks']);
      $('#reward').css('display','inline');
      $('#reward').addClass('alert').addClass('alert-success');
      $('#reward').css('max-width','180px');
      $('#reward').css('margin-top','');
    }
    $('#milestone').html(data['place_milestone'])

  },
  fail: function()
  {
    
    alert('Problem processing request. We are looking into this.');
  }
}).done(function( msg ) {
 // document.getElementById("user_tips").value="";
  //alert("Thanks for helping us improve!");
}); 
}


function send_votes(id,key,type,displayId)
{
    
    var display_vector={'p':'n','n':'p'};
    var score_dict={'p':1,'n':-1};
    if(id=="" || id==null || key=="" || key==null)
    {
        alert("Problem submitting vote. We are looking into this.");
        return;

        
    }
    //toggle display for rating buttons
    $('#'+displayId).css('display','none');
    $('#'+display_vector[displayId.substr(0,1)]+displayId.substr(1)).css('display','');
    var score=parseInt($('#'+displayId).attr('title').split(' ')[1]);
    score=score+score_dict[type];
    $('#'+displayId).attr('title','Score '+score);
    $('#'+display_vector[displayId.substr(0,1)]+displayId.substr(1)).attr('title','Score '+score);
    $.ajax({
  type: "POST",
  url: "/send_votes",
  data: { id:id,key:key,type:type},
  
  success: function()
  {
    
  },
  fail: function()
  {
    
    alert('Problem submitting vote. We are looking into this.');
  }
}).done(function( msg ) {
 // document.getElementById("user_tips").value="";
  //alert("Thanks for helping us improve!");
});
}