$(function(){

	var error_receiver = false;
	var error_addr = false;
	var error_phone = false;

	var $reveiver = $('#receiver');
	var $addr = $('#addr');
	var $phone = $('#phone');

	$reveiver.blur(function() {
		check_receiver();
	});

	$addr.blur(function() {
		check_addr();
	});

	$phone.blur(function() {
		check_phone();
	});


	function check_receiver(){
		var len = $reveiver.val().trim().replace(/\s/g,"").length;
		if(len <= 0)
		{
			$reveiver.next().html('请输入收件人名称')
			$reveiver.next().show();
			error_receiver = true;
		}
		else
		{
			$reveiver.next().hide();
			error_receiver = false;
		}
	}

	function check_addr(){
		var len = $addr.val().trim().replace(/\s/g,"").length;
		if(len <= 0)
		{
			$addr.next().html('请输入收件地址')
			$addr.next().show();
			error_addr = true;
		}
		else
		{
			$addr.next().hide();
			error_addr = false;
		}
	}


	function check_phone(){
		var re = /^1[34578][0-9]{9}$/;

		if(re.test($phone.val()))
		{
			$phone.next().hide();
			error_phone = false;
		}
		else
		{
			$phone.next().html('你输入的手机号码格式不正确')
			$phone.next().show();
			error_phone = true;
		}

	}


	$('#submit').click(function() {
		check_receiver();
		check_addr();
		check_phone();

		return error_receiver === false && error_addr === false && error_phone === false;

	});








})