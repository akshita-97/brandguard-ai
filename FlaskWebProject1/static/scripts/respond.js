/* NUGET: BEGIN LICENSE TEXT
 *
 * Microsoft grants you the right to use these script files for the sole
 * purpose of either: (i) interacting through your browser with the Microsoft
 * website or online service, subject to the applicable licensing or use
 * terms; or (ii) using the files as included with a Microsoft product subject
 * to that product's license terms. Microsoft reserves all other rights to the
 * files not expressly granted by Microsoft, whether by implication, estoppel
 * or otherwise. Insofar as a script file is dual licensed under GPL,
 * Microsoft neither took the code under GPL nor distributes it thereunder but
 * under the terms set out in this paragraph. All notices and licenses
 * below are for informational purposes only.
 *
 * NUGET: END LICENSE TEXT */
/*! matchMedia() polyfill - Test a CSS media type/query in JS. Authors & copyright (c) 2012: Scott Jehl, Paul Irish, Nicholas Zakas. Dual MIT/BSD license */
/*! NOTE: If you're already including a window.matchMedia polyfill via Modernizr or otherwise, you don't need this part */
window.matchMedia = window.matchMedia || (function(doc, undefined){
  
  var bool,
      docElem  = doc.documentElement,
      refNode  = docElem.firstElementChild || docElem.firstChild,
      // fakeBody required for <FF4 when executed in <head>
      fakeBody = doc.createElement('body'),
      div      = doc.createElement('div');
  
  div.id = 'mq-test-1';
  div.style.cssText = "position:absolute;top:-100em";
  fakeBody.style.background = "none";
  fakeBody.appendChild(div);
  
  return function(q){
    
    div.innerHTML = '&shy;<style media="'+q+'"> #mq-test-1 { width: 42px; }</style>';
    
    docElem.insertBefore(fakeBody, refNode);
    bool = div.offsetWidth == 42;  
    docElem.removeChild(fakeBody);
    
    return { matches: bool, media: q };
  };
  
})(document);




/*! Respond.js v1.2.0: min/max-width media query polyfill. (c) Scott Jehl. MIT/GPLv2 Lic. j.mp/respondjs  */
(function( win ){
	//exposed namespace
	win.respond		= {};
	
	//define update even in native-mq-supporting browsers, to avoid errors
	respond.update	= function(){};
	
	//expose media query support flag for external use
	respond.mediaQueriesSupported	= win.matchMedia && win.matchMedia( "only all" ).matches;
	
	//if media queries are supported, exit here
	if( respond.mediaQueriesSupported ){ return; }
	
	//define vars
	var doc 			= win.document,
		docElem 		= doc.documentElement,
		mediastyles		= [],
		rules			= [],
		appendedEls 	= [],
		parsedSheets 	= {},
		resizeThrottle	= 30,
		head 			= doc.getElementsByTagName( "head" )[0] || docElem,
		base			= doc.getElementsByTagName( "base" )[0],
		links			= head.getElementsByTagName( "link" ),
		requestQueue	= [],
		
		//loop stylesheets, send text content to translate
		ripCSS			= function(){
			var sheets 	= links,
				sl 		= sheets.length,
				i		= 0,
				//vars for loop:
				sheet, href, media, isCSS;

			for( ; i < sl; i++ ){
				sheet	= sheets[ i ],
				href	= sheet.href,
				media	= sheet.media,
				isCSS	= sheet.rel && sheet.rel.toLowerCase() === "stylesheet";

				//only links plz and prevent re-parsing
				if( !!href && isCSS && !parsedSheets[ href ] ){
					// selectivizr exposes css through the rawCssText expando
					if (sheet.styleSheet && sheet.styleSheet.rawCssText) {
						translate( sheet.styleSheet.rawCssText, href, media );
						parsedSheets[ href ] = true;
					} else {
						if( (!/^([a-zA-Z:]*\/\/)/.test( href ) && !base)
							|| href.replace( RegExp.$1, "" ).split( "/" )[0] === win.location.host ){
							requestQueue.push( {
								href: href,
								media: media
							} );
						}
					}
				}
			}
			makeRequests();
		},
		
		//recurse through request queue, get css text
		makeRequests	= function(){
			if( requestQueue.length ){
				var thisRequest = requestQueue.shift();
				
				ajax( thisRequest.href, function( styles ){
					translate( styles, thisRequest.href, thisRequest.media );
					parsedSheets[ thisRequest.href ] = true;
					makeRequests();
				} );
			}
		},
		
		//find media blocks in css text, convert to style blocks
		translate			= function( styles, href, media ){
			var qs			= styles.match(  /@media[^\{]+\{([^\{\}]*\{[^\}\{]*\})+/gi ),
				ql			= qs && qs.length || 0,
				//try to get CSS path
				href		= href.substring( 0, href.lastIndexOf( "/" )),
				repUrls		= function( css ){
					return css.replace( /(url\()['"]?([^\/\)'"][^:\)'"]+)['"]?(\))/g, "$1" + href + "$2$3" );
				},
				useMedia	= !ql && media,
				//vars used in loop
				i			= 0,
				j, fullq, thisq, eachq, eql;

			//if path exists, tack on trailing slash
			if( href.length ){ href += "/"; }	
				
			//if no internal queries exist, but media attr does, use that	
			//note: this currently lacks support for situations where a media attr is specified on a link AND
				//its associated stylesheet has internal CSS media queries.
				//In those cases, the media attribute will currently be ignored.
			if( useMedia ){
				ql = 1;
			}
			

			for( ; i < ql; i++ ){
				j	= 0;
				
				//media attr
				if( useMedia ){
					fullq = media;
					rules.push( repUrls( styles ) );
				}
				//parse for styles
				else{
					fullq	= qs[ i ].match( /@media *([^\{]+)\{([\S\s]+?)$/ ) && RegExp.$1;
					rules.push( RegExp.$2 && repUrls( RegExp.$2 ) );
				}
				
				eachq	= fullq.split( "," );
				eql		= eachq.length;
					
				for( ; j < eql; j++ ){
					thisq	= eachq[ j ];
					mediastyles.push( { 
						media	: thisq.split( "(" )[ 0 ].match( /(only\s+)?([a-zA-Z]+)\s?/ ) && RegExp.$2 || "all",
						rules	: rules.length - 1,
						hasquery: thisq.indexOf("(") > -1,
						minw	: thisq.match( /\(min\-width:[\s]*([\s]*[0-9\.]+)(px|em)[\s]*\)/ ) && parseFloat( RegExp.$1 ) + ( RegExp.$2 || "" ), 
						maxw	: thisq.match( /\(max\-width:[\s]*([\s]*[0-9\.]+)(px|em)[\s]*\)/ ) && parseFloat( RegExp.$1 ) + ( RegExp.$2 || "" )
					} );
				}	
			}

			applyMedia();
		},
        	
		lastCall,
		
		resizeDefer,
		
		// returns the value of 1em in pixels
		getEmValue		= function() {
			var ret,
				div = doc.createElement('div'),
				body = doc.body,
				fakeUsed = false;
									
			div.style.cssText = "position:absolute;font-size:1em;width:1em";
					
			if( !body ){
				body = fakeUsed = doc.createElement( "body" );
				body.style.background = "none";
			}
					
			body.appendChild( div );
								
			docElem.insertBefore( body, docElem.firstChild );
								
			ret = div.offsetWidth;
								
			if( fakeUsed ){
				docElem.removeChild( body );
			}
			else {
				body.removeChild( div );
			}
			
			//also update eminpx before returning
			ret = eminpx = parseFloat(ret);
								
			return ret;
		},
		
		//cached container for 1em value, populated the first time it's needed 
		eminpx,
		
		//enable/disable styles
		applyMedia			= function( fromResize ){
			var name		= "clientWidth",
				docElemProp	= docElem[ name ],
				currWidth 	= doc.compatMode === "CSS1Compat" && docElemProp || doc.body[ name ] || docElemProp,
				styleBlocks	= {},
				lastLink	= links[ links.length-1 ],
				now 		= (new Date()).getTime();

			//throttle resize calls	
			if( fromResize && lastCall && now - lastCall < resizeThrottle ){
				clearTimeout( resizeDefer );
				resizeDefer = setTimeout( applyMedia, resizeThrottle );
				return;
			}
			else {
				lastCall	= now;
			}
										
			for( var i in mediastyles ){
				var thisstyle = mediastyles[ i ],
					min = thisstyle.minw,
					max = thisstyle.maxw,
					minnull = min === null,
					maxnull = max === null,
					em = "em";
				
				if( !!min ){
					min = parseFloat( min ) * ( min.indexOf( em ) > -1 ? ( eminpx || getEmValue() ) : 1 );
				}
				if( !!max ){
					max = parseFloat( max ) * ( max.indexOf( em ) > -1 ? ( eminpx || getEmValue() ) : 1 );
				}
				
				// if there's no media query at all (the () part), or min or max is not null, and if either is present, they're true
				if( !thisstyle.hasquery || ( !minnull || !maxnull ) && ( minnull || currWidth >= min ) && ( maxnull || currWidth <= max ) ){
						if( !styleBlocks[ thisstyle.media ] ){
							styleBlocks[ thisstyle.media ] = [];
						}
						styleBlocks[ thisstyle.media ].push( rules[ thisstyle.rules ] );
				}
			}
			
			//remove any existing respond style element(s)
			for( var i in appendedEls ){
				if( appendedEls[ i ] && appendedEls[ i ].parentNode === head ){
					head.removeChild( appendedEls[ i ] );
				}
			}
			
			//inject active styles, grouped by media type
			for( var i in styleBlocks ){
				var ss		= doc.createElement( "style" ),
					css		= styleBlocks[ i ].join( "\n" );
				
				ss.type = "text/css";	
				ss.media	= i;
				
				//originally, ss was appended to a documentFragment and sheets were appended in bulk.
				//this caused crashes in IE in a number of circumstances, such as when the HTML element had a bg image set, so appending beforehand seems best. Thanks to @dvelyk for the initial research on this one!
				head.insertBefore( ss, lastLink.nextSibling );
				
				if ( ss.styleSheet ){ 
		        	ss.styleSheet.cssText = css;
		        } 
		        else {
					ss.appendChild( doc.createTextNode( css ) );
		        }
		        
				//push to appendedEls to track for later removal
				appendedEls.push( ss );
			}
		},
		//tweaked Ajax functions from Quirksmode
		ajax = function( url, callback ) {
			var req = xmlHttp();
			if (!req){
				return;
			}	
			req.open( "GET", url, true );
			req.onreadystatechange = function () {
				if ( req.readyState != 4 || req.status != 200 && req.status != 304 ){
					return;
				}
				callback( req.responseText );
			}
			if ( req.readyState == 4 ){
				return;
			}
			req.send( null );
		},
		//define ajax obj 
		xmlHttp = (function() {
			var xmlhttpmethod = false;	
			try {
				xmlhttpmethod = new XMLHttpRequest();
			}
			catch( e ){
				xmlhttpmethod = new ActiveXObject( "Microsoft.XMLHTTP" );
			}
			return function(){
				return xmlhttpmethod;
			};
		})();
	
	//translate CSS
	ripCSS();
	
	//expose update for re-running respond later on
	respond.update = ripCSS;
	
	//adjust on resize
	function callMedia(){
		applyMedia( true );
	}
	if( win.addEventListener ){
		win.addEventListener( "resize", callMedia, false );
	}
	else if( win.attachEvent ){
		win.attachEvent( "onresize", callMedia );
	}
})(this);

// SIG // Begin signature block
// SIG // MIInggYJKoZIhvcNAQcCoIInczCCJ28CAQExDzANBglg
// SIG // hkgBZQMEAgEFADB3BgorBgEEAYI3AgEEoGkwZzAyBgor
// SIG // BgEEAYI3AgEeMCQCAQEEEBDgyQbOONQRoqMAEEvTUJAC
// SIG // AQACAQACAQACAQACAQAwMTANBglghkgBZQMEAgEFAAQg
// SIG // w3y8PXLL3CtA/3Hg+8ZTHHP4KbtNHdPwcW38NSVz/yGg
// SIG // ggzeMIIGGTCCBAGgAwIBAgITMwAAAf3k91kxw2Tc4QAA
// SIG // AAAB/TANBgkqhkiG9w0BAQsFADBXMQswCQYDVQQGEwJV
// SIG // UzEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9u
// SIG // MSgwJgYDVQQDEx9NaWNyb3NvZnQgQ29kZSBTaWduaW5n
// SIG // IFBDQSAyMDI0MB4XDTI2MDQxNjE4NTg1MVoXDTI3MDQx
// SIG // NTE4NTg1MVowgYgxCzAJBgNVBAYTAlVTMRMwEQYDVQQI
// SIG // EwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRtb25kMR4w
// SIG // HAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24xMjAw
// SIG // BgNVBAMTKU1pY3Jvc29mdCAzcmQgUGFydHkgQXBwbGlj
// SIG // YXRpb24gQ29tcG9uZW50MIIBIjANBgkqhkiG9w0BAQEF
// SIG // AAOCAQ8AMIIBCgKCAQEAySyr5uf9sXckExv7VIrrr8Oq
// SIG // IRrb95I5+Ognua2kG0Q9rU80bzMLdSjaeKKjPOUaTswc
// SIG // fzSmqsxDkUlMBw/NsOS5lrR89dqEEtRg6WdJvwPVFiJf
// SIG // wOjYkgFFY7FZgfUnXcRyZ01b9mfi9a7Xnkp8HqGDGMXX
// SIG // D9HyNjP9KoKrdORqrkHOCNDFqyF/zEKbye9S5tvmom3B
// SIG // G1IhObqlRZYYhFqANjNv1ogX4zJEll7Nk5u5awit9+e5
// SIG // FzxqeqrXFhyyAbWZoY39txBUIjsabUX7F5hiF1qLqLV1
// SIG // cgAV/X6N5eYAVEbLpKT/QJTuKTHhndYDHADLPPM2pe0X
// SIG // BogfjnMMpwIDAQABo4IBqjCCAaYwDgYDVR0PAQH/BAQD
// SIG // AgeAMB8GA1UdJQQYMBYGCisGAQQBgjdMEQEGCCsGAQUF
// SIG // BwMDMB0GA1UdDgQWBBQQBjHV6tDXOT4+/NSMkbW//6Co
// SIG // 5jBUBgNVHREETTBLpEkwRzEtMCsGA1UECxMkTWljcm9z
// SIG // b2Z0IElyZWxhbmQgT3BlcmF0aW9ucyBMaW1pdGVkMRYw
// SIG // FAYDVQQFEw0yMzE1MjIrNTA3NTQxMB8GA1UdIwQYMBaA
// SIG // FH9ZP1Qh2q1P7wXl5qPXLQaUEggxMGAGA1UdHwRZMFcw
// SIG // VaBToFGGT2h0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9w
// SIG // a2lvcHMvY3JsL01pY3Jvc29mdCUyMENvZGUlMjBTaWdu
// SIG // aW5nJTIwUENBJTIwMjAyNC5jcmwwbQYIKwYBBQUHAQEE
// SIG // YTBfMF0GCCsGAQUFBzAChlFodHRwOi8vd3d3Lm1pY3Jv
// SIG // c29mdC5jb20vcGtpb3BzL2NlcnRzL01pY3Jvc29mdCUy
// SIG // MENvZGUlMjBTaWduaW5nJTIwUENBJTIwMjAyNC5jcnQw
// SIG // DAYDVR0TAQH/BAIwADANBgkqhkiG9w0BAQsFAAOCAgEA
// SIG // y174mRjWUCxBQDnYClZpU26m2coMTq0BN1Y+gUFRlfp9
// SIG // H3kGXx1tALbQUmpB9hx4YfjoBoJ6BhQou8UevkCjSRkY
// SIG // QTxRzycyJ65aNkvK7I0bmHj36kIlkUuc6OzpbYUqTYrQ
// SIG // oB7IeltYP9dsKgzYR838mnynQg+n1UMfp0cFlNBc7T5D
// SIG // Km2bTL+SIVzjOWKdgv3VZvXDXVgtgLLmoFnlj0/Nkz/s
// SIG // xqiQEMxI8M+FsIGgRy/UAPgJAlZ5PCrcFf7jkQMU4roy
// SIG // jZH8eoiiLCUc/Z17Ml+huLGOthtJm+VzwY/2UiR1xRic
// SIG // eAh6htMkjujyBZ+N1VWwYe8y9fqu9huswNtvw+W7pJ9F
// SIG // 7ZFT3BQvszCPMqIMF+mNYI9jI2S5uIHeCNSykgPmJT1C
// SIG // MYXmJxt/CNgKho8zcCfJPdhc0CYSHZanQVdIikSR8ACN
// SIG // 4dSj84XThqNJgmMy3XTLBEJNnnU7FzoaRXeI6BXKYTOU
// SIG // 3HrTEhbXzJABMwp6HiRCIS7JX+7nRkW4JRW+RcXtbp7V
// SIG // aexrehTgfm6BBdM4d/uQJJ8B0TR5GSvemvi9XOSH70d0
// SIG // J7IYyIJ6/xPB6Lhe0CZMcPa4NsT+FgW8ek+vdbzYHHua
// SIG // HaIb5wpe8WweS4uO3jDmEmDm7jGcWaOgwPqxL0XoYeTF
// SIG // beFXTcAS432qwkF6xEpDwk4wgga9MIIEpaADAgECAhMz
// SIG // AAAAOTu2Nxm/Bh1nAAAAAAA5MA0GCSqGSIb3DQEBDAUA
// SIG // MIGIMQswCQYDVQQGEwJVUzETMBEGA1UECBMKV2FzaGlu
// SIG // Z3RvbjEQMA4GA1UEBxMHUmVkbW9uZDEeMBwGA1UEChMV
// SIG // TWljcm9zb2Z0IENvcnBvcmF0aW9uMTIwMAYDVQQDEylN
// SIG // aWNyb3NvZnQgUm9vdCBDZXJ0aWZpY2F0ZSBBdXRob3Jp
// SIG // dHkgMjAxMTAeFw0yNDA4MDgyMDU0MThaFw0zNjAzMjIy
// SIG // MjEzMDRaMFcxCzAJBgNVBAYTAlVTMR4wHAYDVQQKExVN
// SIG // aWNyb3NvZnQgQ29ycG9yYXRpb24xKDAmBgNVBAMTH01p
// SIG // Y3Jvc29mdCBDb2RlIFNpZ25pbmcgUENBIDIwMjQwggIi
// SIG // MA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDYAZwe
// SIG // 4zjHqpUWBzWtuub+CGPXx/EyoXph3zyDXtYKS2ld3YYN
// SIG // 9uFsB9Oi3B26Z7AbpAgzYra8qNHbUvxFuiP8hC/2y0mP
// SIG // ISqW30LlrrAT6/ams2HA8Qlv6p42+SbCNbPGzToN21QE
// SIG // 70FS+LXH9N2k8nLM/EHgnTNJf8h0TmyfUKmszNa+lTxD
// SIG // ieyy/rhBG+98OkArobPPWtbr9c3qzmDJ7J3kUcAm6clt
// SIG // dSHIIFNHESgw6taY1ScyGyBevqIl120XjrIHiPM7tRck
// SIG // HytH1ZGsmvEplR0P7Tn9t5meFvZNEYttkFvad1IEguTl
// SIG // A5LSscXAphi+rVy3zhklhyCFeGK0yU0+jzbcuURKIxyb
// SIG // mRwK5BfVZx0xEVqE4wM3yN5D/uW+GpVHYYAGe7bTrtW1
// SIG // Z13x2qj2Jdqz7NtI4tNyzlVrIf62nYBNe3rOYS/repVd
// SIG // HlR61YbLLETlibs9jFzAre4sO5RTxvS1yho7JqJ59oKL
// SIG // RnRyLhIOSZyTCVZosXeS0ZZJoGEWSs4cUgsMqBiKtD4W
// SIG // gO2PlT3LeaQh5Io3CCA5tJ5ZCvtCsnqaJXKhptE/xmEE
// SIG // TIRyZRjjplUKKd+sFFVGJJVMvvrw1nhIBKOLO4cTepiG
// SIG // 39jEiEP4iHzGYCcQuvaLpDFFwqzgt0pBP8SJIKX5dtjD
// SIG // NYrZGd+ZzV5DKJVNZQIDAQABo4IBTjCCAUowDgYDVR0P
// SIG // AQH/BAQDAgGGMBAGCSsGAQQBgjcVAQQDAgEAMB0GA1Ud
// SIG // DgQWBBR/WT9UIdqtT+8F5eaj1y0GlBIIMTAZBgkrBgEE
// SIG // AYI3FAIEDB4KAFMAdQBiAEMAQTAPBgNVHRMBAf8EBTAD
// SIG // AQH/MB8GA1UdIwQYMBaAFHItOgIxkEO5FAVO4eqnxzHR
// SIG // I4k0MFoGA1UdHwRTMFEwT6BNoEuGSWh0dHA6Ly9jcmwu
// SIG // bWljcm9zb2Z0LmNvbS9wa2kvY3JsL3Byb2R1Y3RzL01p
// SIG // Y1Jvb0NlckF1dDIwMTFfMjAxMV8wM18yMi5jcmwwXgYI
// SIG // KwYBBQUHAQEEUjBQME4GCCsGAQUFBzAChkJodHRwOi8v
// SIG // d3d3Lm1pY3Jvc29mdC5jb20vcGtpL2NlcnRzL01pY1Jv
// SIG // b0NlckF1dDIwMTFfMjAxMV8wM18yMi5jcnQwDQYJKoZI
// SIG // hvcNAQEMBQADggIBABSUHzgoT+6J5+nyyDCq0pTdVmCs
// SIG // AxYAHXcpjlDtxazPHewf1v4kOg8V7A5+w+VuMDMGHi8r
// SIG // LXBKn5I8+DVEUYGs8jLuckc0IeC6owOLUrU3CYdaKRMa
// SIG // O55+T7jwWJ27tPkx0rlR03tFU0z1YYpcv6Yhaw6N2sUP
// SIG // T+AvjpecnrftoE33pCAkucUvnGH0iL4J9CZLFQVTGFSO
// SIG // UBbv6oZy4bBBRFMxvH779IY4JDvpZKVfbcuhpDeL3Z3e
// SIG // 8mukOmkfct+GojNapsWsQYujlJ8jZen5Lrp/3YkxZ2Ay
// SIG // 06aTpK/5oOVknwog1TDQsbY+MDyguTph5tQ0CLfzDaJG
// SIG // 2x91BrBT9UG87C6HLkqiwrx9PSKN3wz05rHEfWO+RuKl
// SIG // +0U1/AHQT6NCOjhKI39/c7hWbdKjh5uuWFkBOvXGTNrn
// SIG // hNTAdOXTTYByvYExO8yryv34PAdqo1vPDE/1heVebr2R
// SIG // ramvRUi9kWswKwPqwz7n+iRmM+B6YDGRweEurM1kimAb
// SIG // 9FYrAs38YHlPnarl1vW3dGrmJTgefAz3DmCnXN0nveIP
// SIG // sS+KXBIWweeCToAJMGE7v/XS3h9qQ6niWQAAVQ1kUAml
// SIG // 3zuS4MisCgi2F6YoK2WAo1EgXK/lXvDxVjIVU0JdL+Kv
// SIG // CfwFJkDeVuJ9dNXGNi+AOxk0BtYd9hxwL30BElj9MYIZ
// SIG // /DCCGfgCAQEwbjBXMQswCQYDVQQGEwJVUzEeMBwGA1UE
// SIG // ChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSgwJgYDVQQD
// SIG // Ex9NaWNyb3NvZnQgQ29kZSBTaWduaW5nIFBDQSAyMDI0
// SIG // AhMzAAAB/eT3WTHDZNzhAAAAAAH9MA0GCWCGSAFlAwQC
// SIG // AQUAoIGuMBkGCSqGSIb3DQEJAzEMBgorBgEEAYI3AgEE
// SIG // MBwGCisGAQQBgjcCAQsxDjAMBgorBgEEAYI3AgEVMC8G
// SIG // CSqGSIb3DQEJBDEiBCA2uWfYsEn+Xqg6P//C2jtJIrew
// SIG // z8Q0sF/iUjrUTPxzSzBCBgorBgEEAYI3AgEMMTQwMqAU
// SIG // gBIATQBpAGMAcgBvAHMAbwBmAHShGoAYaHR0cDovL3d3
// SIG // dy5taWNyb3NvZnQuY29tMA0GCSqGSIb3DQEBAQUABIIB
// SIG // AB5prmxcqGJGtxHThQk+YgzFf+LuPlaFRpV4MtpSDw5n
// SIG // rLAIedVBD5uizY9SyThaAxwucmOuv0XAelSz7PfL+3sN
// SIG // AZjZoI8EBqSpyddIx1wmKZHEtIByfP1FbHhG0F5lBa2f
// SIG // +WGZOaUf6R3L7KuQ9rBeKCsvdYfeK/8KCovLU/Y7pn2r
// SIG // XvBy+7MA/9OqvP1CVg3Ontz+gz+uuDCNOi6x/2GhO1bB
// SIG // pLQtHcZr0YCQEFXV8KfjjkC2MuYixXogwEusCwcJdf3j
// SIG // SeSQ2rR+tMVcm7IPCB9P1SPofPi/4dKfQ+N2yAEFPcqJ
// SIG // qIv4b0SoJ9ilQ557H5gKBTnJKav9nzcCXCqhgheuMIIX
// SIG // qgYKKwYBBAGCNwMDATGCF5owgheWBgkqhkiG9w0BBwKg
// SIG // gheHMIIXgwIBAzEPMA0GCWCGSAFlAwQCAQUAMIIBWAYL
// SIG // KoZIhvcNAQkQAQSgggFHBIIBQzCCAT8CAQEGCisGAQQB
// SIG // hFkKAwEwMTANBglghkgBZQMEAgEFAAQgi1BAOEwFbB1s
// SIG // przaU02Vrc2yJPwuyiwQsEwU7VAtvq8CBmpjpbw7ZhgR
// SIG // MjAyNjA4MTAxODIxMjIuNFowBIACAfSggdmkgdYwgdMx
// SIG // CzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpXYXNoaW5ndG9u
// SIG // MRAwDgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVNaWNy
// SIG // b3NvZnQgQ29ycG9yYXRpb24xLTArBgNVBAsTJE1pY3Jv
// SIG // c29mdCBJcmVsYW5kIE9wZXJhdGlvbnMgTGltaXRlZDEn
// SIG // MCUGA1UECxMeblNoaWVsZCBUU1MgRVNOOjMyMUEtMDVF
// SIG // MC1EOTQ3MSUwIwYDVQQDExxNaWNyb3NvZnQgVGltZS1T
// SIG // dGFtcCBTZXJ2aWNloIIR/jCCBygwggUQoAMCAQICEzMA
// SIG // AAIaqaAdBqAPQ6oAAQAAAhowDQYJKoZIhvcNAQELBQAw
// SIG // fDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCldhc2hpbmd0
// SIG // b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1p
// SIG // Y3Jvc29mdCBDb3Jwb3JhdGlvbjEmMCQGA1UEAxMdTWlj
// SIG // cm9zb2Z0IFRpbWUtU3RhbXAgUENBIDIwMTAwHhcNMjUw
// SIG // ODE0MTg0ODI4WhcNMjYxMTEzMTg0ODI4WjCB0zELMAkG
// SIG // A1UEBhMCVVMxEzARBgNVBAgTCldhc2hpbmd0b24xEDAO
// SIG // BgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1pY3Jvc29m
// SIG // dCBDb3Jwb3JhdGlvbjEtMCsGA1UECxMkTWljcm9zb2Z0
// SIG // IElyZWxhbmQgT3BlcmF0aW9ucyBMaW1pdGVkMScwJQYD
// SIG // VQQLEx5uU2hpZWxkIFRTUyBFU046MzIxQS0wNUUwLUQ5
// SIG // NDcxJTAjBgNVBAMTHE1pY3Jvc29mdCBUaW1lLVN0YW1w
// SIG // IFNlcnZpY2UwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAw
// SIG // ggIKAoICAQCZgQDBJPPv2rZXdlbNDkS/tEqBp1C0wHLv
// SIG // 5XddDxHQ0vxH2a6nFyolD8o95kYlMRH71Cr+3sc5B8Fs
// SIG // PLp7RN6m8EVX9FjfD4s48wqfRSiHb/wi91JsnyoBZFWj
// SIG // PZL1WsnNmkHz9/mtBxEROBf+3w3roPYmURe/h9lAHtfN
// SIG // wkxevWm6G5ds631FgTI3VDdntiNGSF8GxFz5IP8L0XiL
// SIG // Bmp9CCjzYYbjCC4iGMlTv5cx+u/i/EAU1WDeafU+gxYZ
// SIG // laKj57Xj48Zg9UsqVp37QiF0crkCA/JcqSoCERmliFhh
// SIG // UQi0c46+qvC6TFUAlcy9YDcZq1aRFmffdYMlW2CEJbpc
// SIG // 8uLVwMqIYTlRxdlJXg6NAhQHy+nYtQxFe53kjj0UgFwT
// SIG // 2dPTTPwD4R6Ss8z44CTTtoN/Blt2ZnnqPu5vl80Mt/zI
// SIG // hvxDFnwyvhHBbL9zMG5XmuRZBD6ayMnkAq1hnEl2dpl6
// SIG // FSBQ0CtT+7fpIfV5coxAZFev/F4oUYjy++/kmXWSdnxS
// SIG // oRCv0/ENuKzs5enZZIwrmUsZ1hUfxWjCdgXexs6JGTHl
// SIG // DkZoTJN6E5CnZJ91uwlmWDRJeYemEaehbX+BD/k/oGBK
// SIG // rg8BYhloMmPoC8ssJ1tRGBHlqk1BB53bNhSBRuMAID9O
// SIG // iYDwuXsCuu/ahkaJQ7lV2LjHG0DcFFNBNQIDAQABo4IB
// SIG // STCCAUUwHQYDVR0OBBYEFPCrIgndAyg9qwNwZ0ai9tpj
// SIG // wiU2MB8GA1UdIwQYMBaAFJ+nFV0AXmJdg/Tl0mWnG1M1
// SIG // GelyMF8GA1UdHwRYMFYwVKBSoFCGTmh0dHA6Ly93d3cu
// SIG // bWljcm9zb2Z0LmNvbS9wa2lvcHMvY3JsL01pY3Jvc29m
// SIG // dCUyMFRpbWUtU3RhbXAlMjBQQ0ElMjAyMDEwKDEpLmNy
// SIG // bDBsBggrBgEFBQcBAQRgMF4wXAYIKwYBBQUHMAKGUGh0
// SIG // dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMvY2Vy
// SIG // dHMvTWljcm9zb2Z0JTIwVGltZS1TdGFtcCUyMFBDQSUy
// SIG // MDIwMTAoMSkuY3J0MAwGA1UdEwEB/wQCMAAwFgYDVR0l
// SIG // AQH/BAwwCgYIKwYBBQUHAwgwDgYDVR0PAQH/BAQDAgeA
// SIG // MA0GCSqGSIb3DQEBCwUAA4ICAQDVrvZYWrsHpslPdU4n
// SIG // bWedOg8n07+rnVvDVuE99DLru7L5/zHxqSKnM0vaTlvq
// SIG // a3G49tkakGqkEqC4PBCbFWlfxwaZp96jfAavhrxiTpLL
// SIG // T20SH83DCWzKrsFGsk2fpsY4HyIbg5PL6mYxSHsV6M09
// SIG // GC+B6j84/K2bg02swyD3xRWWtnEY05iyJ+lEkWDmMT9i
// SIG // 7qWoVrWVOb1we49jFZragTALSwQCxMVvr2Iqk3Sw7X3E
// SIG // FkKvSHkKVT0+Cjp6SIlvtAmgPOsOg9AfBs0DzsK2jtMu
// SIG // 6mGPSb2X8jvSAuMSrndIeO5RHPCmY3F2bXxCD6uWRowL
// SIG // pjYq6Q58nugJK729w0ZAz6KeX2Cw2CKtnrImT1WxcSyh
// SIG // O2hHt8w1To/Lq58lAYxOarpkKrZ4gY5dYwFvv1kXq2Ip
// SIG // NripqaLdRLSZNjjUnXb1eYCCVXL66NJmQe7aUckNEezs
// SIG // WOchdlVQTmmXrJQiXbeMbnR9FMtBxK13Bj8u8lSAQcIj
// SIG // OO+UtOou3olVHltyzlo3gOHRg8b3kH2IMxmuriuWLlKc
// SIG // Y1Z6/ksuwNjV9usrq5WkP6my9Iuw2mG3btBwdGxh0AwA
// SIG // tcz4c2zPYtnzGI5/C3qs6xVZeiIdXzr9N4zLlNkVSXuo
// SIG // Hn0g2gxImANGVp1Vd5P1/A66KsUiiqCMoaTe87ZsQutg
// SIG // w3RBXDCCB3EwggVZoAMCAQICEzMAAAAVxedrngKbSZkA
// SIG // AAAAABUwDQYJKoZIhvcNAQELBQAwgYgxCzAJBgNVBAYT
// SIG // AlVTMRMwEQYDVQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQH
// SIG // EwdSZWRtb25kMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29y
// SIG // cG9yYXRpb24xMjAwBgNVBAMTKU1pY3Jvc29mdCBSb290
// SIG // IENlcnRpZmljYXRlIEF1dGhvcml0eSAyMDEwMB4XDTIx
// SIG // MDkzMDE4MjIyNVoXDTMwMDkzMDE4MzIyNVowfDELMAkG
// SIG // A1UEBhMCVVMxEzARBgNVBAgTCldhc2hpbmd0b24xEDAO
// SIG // BgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1pY3Jvc29m
// SIG // dCBDb3Jwb3JhdGlvbjEmMCQGA1UEAxMdTWljcm9zb2Z0
// SIG // IFRpbWUtU3RhbXAgUENBIDIwMTAwggIiMA0GCSqGSIb3
// SIG // DQEBAQUAA4ICDwAwggIKAoICAQDk4aZM57RyIQt5osvX
// SIG // JHm9DtWC0/3unAcH0qlsTnXIyjVX9gF/bErg4r25Phdg
// SIG // M/9cT8dm95VTcVrifkpa/rg2Z4VGIwy1jRPPdzLAEBjo
// SIG // YH1qUoNEt6aORmsHFPPFdvWGUNzBRMhxXFExN6AKOG6N
// SIG // 7dcP2CZTfDlhAnrEqv1yaa8dq6z2Nr41JmTamDu6Gnsz
// SIG // rYBbfowQHJ1S/rboYiXcag/PXfT+jlPP1uyFVk3v3byN
// SIG // pOORj7I5LFGc6XBpDco2LXCOMcg1KL3jtIckw+DJj361
// SIG // VI/c+gVVmG1oO5pGve2krnopN6zL64NF50ZuyjLVwIYw
// SIG // XE8s4mKyzbnijYjklqwBSru+cakXW2dg3viSkR4dPf0g
// SIG // z3N9QZpGdc3EXzTdEonW/aUgfX782Z5F37ZyL9t9X4C6
// SIG // 26p+Nuw2TPYrbqgSUei/BQOj0XOmTTd0lBw0gg/wEPK3
// SIG // Rxjtp+iZfD9M269ewvPV2HM9Q07BMzlMjgK8QmguEOqE
// SIG // UUbi0b1qGFphAXPKZ6Je1yh2AuIzGHLXpyDwwvoSCtdj
// SIG // bwzJNmSLW6CmgyFdXzB0kZSU2LlQ+QuJYfM2BjUYhEfb
// SIG // 3BvR/bLUHMVr9lxSUV0S2yW6r1AFemzFER1y7435UsSF
// SIG // F5PAPBXbGjfHCBUYP3irRbb1Hode2o+eFnJpxq57t7c+
// SIG // auIurQIDAQABo4IB3TCCAdkwEgYJKwYBBAGCNxUBBAUC
// SIG // AwEAATAjBgkrBgEEAYI3FQIEFgQUKqdS/mTEmr6CkTxG
// SIG // NSnPEP8vBO4wHQYDVR0OBBYEFJ+nFV0AXmJdg/Tl0mWn
// SIG // G1M1GelyMFwGA1UdIARVMFMwUQYMKwYBBAGCN0yDfQEB
// SIG // MEEwPwYIKwYBBQUHAgEWM2h0dHA6Ly93d3cubWljcm9z
// SIG // b2Z0LmNvbS9wa2lvcHMvRG9jcy9SZXBvc2l0b3J5Lmh0
// SIG // bTATBgNVHSUEDDAKBggrBgEFBQcDCDAZBgkrBgEEAYI3
// SIG // FAIEDB4KAFMAdQBiAEMAQTALBgNVHQ8EBAMCAYYwDwYD
// SIG // VR0TAQH/BAUwAwEB/zAfBgNVHSMEGDAWgBTV9lbLj+ii
// SIG // XGJo0T2UkFvXzpoYxDBWBgNVHR8ETzBNMEugSaBHhkVo
// SIG // dHRwOi8vY3JsLm1pY3Jvc29mdC5jb20vcGtpL2NybC9w
// SIG // cm9kdWN0cy9NaWNSb29DZXJBdXRfMjAxMC0wNi0yMy5j
// SIG // cmwwWgYIKwYBBQUHAQEETjBMMEoGCCsGAQUFBzAChj5o
// SIG // dHRwOi8vd3d3Lm1pY3Jvc29mdC5jb20vcGtpL2NlcnRz
// SIG // L01pY1Jvb0NlckF1dF8yMDEwLTA2LTIzLmNydDANBgkq
// SIG // hkiG9w0BAQsFAAOCAgEAnVV9/Cqt4SwfZwExJFvhnnJL
// SIG // /Klv6lwUtj5OR2R4sQaTlz0xM7U518JxNj/aZGx80HU5
// SIG // bbsPMeTCj/ts0aGUGCLu6WZnOlNN3Zi6th542DYunKmC
// SIG // VgADsAW+iehp4LoJ7nvfam++Kctu2D9IdQHZGN5tggz1
// SIG // bSNU5HhTdSRXud2f8449xvNo32X2pFaq95W2KFUn0CS9
// SIG // QKC/GbYSEhFdPSfgQJY4rPf5KYnDvBewVIVCs/wMnosZ
// SIG // iefwC2qBwoEZQhlSdYo2wh3DYXMuLGt7bj8sCXgU6ZGy
// SIG // qVvfSaN0DLzskYDSPeZKPmY7T7uG+jIa2Zb0j/aRAfbO
// SIG // xnT99kxybxCrdTDFNLB62FD+CljdQDzHVG2dY3RILLFO
// SIG // Ry3BFARxv2T5JL5zbcqOCb2zAVdJVGTZc9d/HltEAY5a
// SIG // GZFrDZ+kKNxnGSgkujhLmm77IVRrakURR6nxt67I6Ile
// SIG // T53S0Ex2tVdUCbFpAUR+fKFhbHP+CrvsQWY9af3LwUFJ
// SIG // fn6Tvsv4O+S3Fb+0zj6lMVGEvL8CwYKiexcdFYmNcP7n
// SIG // tdAoGokLjzbaukz5m/8K6TT4JDVnK+ANuOaMmdbhIurw
// SIG // J0I9JZTmdHRbatGePu1+oDEzfbzL6Xu/OHBE0ZDxyKs6
// SIG // ijoIYn/ZcGNTTY3ugm2lBRDBcQZqELQdVTNYs6FwZvKh
// SIG // ggNZMIICQQIBATCCAQGhgdmkgdYwgdMxCzAJBgNVBAYT
// SIG // AlVTMRMwEQYDVQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQH
// SIG // EwdSZWRtb25kMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29y
// SIG // cG9yYXRpb24xLTArBgNVBAsTJE1pY3Jvc29mdCBJcmVs
// SIG // YW5kIE9wZXJhdGlvbnMgTGltaXRlZDEnMCUGA1UECxMe
// SIG // blNoaWVsZCBUU1MgRVNOOjMyMUEtMDVFMC1EOTQ3MSUw
// SIG // IwYDVQQDExxNaWNyb3NvZnQgVGltZS1TdGFtcCBTZXJ2
// SIG // aWNloiMKAQEwBwYFKw4DAhoDFQDxiu62YqlKu5sJoBix
// SIG // Tim3UW3wNqCBgzCBgKR+MHwxCzAJBgNVBAYTAlVTMRMw
// SIG // EQYDVQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRt
// SIG // b25kMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRp
// SIG // b24xJjAkBgNVBAMTHU1pY3Jvc29mdCBUaW1lLVN0YW1w
// SIG // IFBDQSAyMDEwMA0GCSqGSIb3DQEBCwUAAgUA7iSMKjAi
// SIG // GA8yMDI2MDgxMDE3NDMwNloYDzIwMjYwODExMTc0MzA2
// SIG // WjB3MD0GCisGAQQBhFkKBAExLzAtMAoCBQDuJIwqAgEA
// SIG // MAoCAQACAhQ5AgH/MAcCAQACAhJJMAoCBQDuJd2qAgEA
// SIG // MDYGCisGAQQBhFkKBAIxKDAmMAwGCisGAQQBhFkKAwKg
// SIG // CjAIAgEAAgMHoSChCjAIAgEAAgMBhqAwDQYJKoZIhvcN
// SIG // AQELBQADggEBAIex76AfqtDsIMKBdjIl4CB6rZAarQ7v
// SIG // p3oPs5q4NNy+Inv+yC13PlJM+nSYCymteQUrbVcaU6W+
// SIG // 5cmS9vC01FbNLERUF97KuHUXnWI2GAGHLaHd8+MqSPrU
// SIG // ZAd5z0yy/FO5C5IkGW9SZPv2a6Ni/hP7TjZckEvLZsov
// SIG // hw6TFVoskAZPP0+uT1Cund7qSceKG1PSAidLinHgfJ5V
// SIG // 7DjR5hDJDztwUEPG222Oou6Wu8hPzHN2KjLeGHnPEtva
// SIG // HYNzDTlmWQv+8fSobfngyxR7rBJEt0cZQYVXU0wJ3jye
// SIG // LgyM4mBYNPgvdyy+UYv7lRWBylA/sZokaWLpUKkJAooD
// SIG // HL0xggQNMIIECQIBATCBkzB8MQswCQYDVQQGEwJVUzET
// SIG // MBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UEBxMHUmVk
// SIG // bW9uZDEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0
// SIG // aW9uMSYwJAYDVQQDEx1NaWNyb3NvZnQgVGltZS1TdGFt
// SIG // cCBQQ0EgMjAxMAITMwAAAhqpoB0GoA9DqgABAAACGjAN
// SIG // BglghkgBZQMEAgEFAKCCAUowGgYJKoZIhvcNAQkDMQ0G
// SIG // CyqGSIb3DQEJEAEEMC8GCSqGSIb3DQEJBDEiBCAhBzfb
// SIG // C7T4MSYfUmbZ52XxcbAxAS0/cq5e6S0oKlkiWTCB+gYL
// SIG // KoZIhvcNAQkQAi8xgeowgecwgeQwgb0EIJ16Icetu2kp
// SIG // zAHbR2hVTz1Ycg4fxLvDfu5odwOZ6Yr7MIGYMIGApH4w
// SIG // fDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCldhc2hpbmd0
// SIG // b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1p
// SIG // Y3Jvc29mdCBDb3Jwb3JhdGlvbjEmMCQGA1UEAxMdTWlj
// SIG // cm9zb2Z0IFRpbWUtU3RhbXAgUENBIDIwMTACEzMAAAIa
// SIG // qaAdBqAPQ6oAAQAAAhowIgQgoE9mif2mf7laLdt1rg0B
// SIG // hipPnzr6xXMkoQY4HYViaNYwDQYJKoZIhvcNAQELBQAE
// SIG // ggIAOtNzE2fp4NNeKvHXdxu9eNfHWPlZuNYMv+FNAwe5
// SIG // imkV9RyUS72Lt9gLb4r7aCBzvyaVtHBJOkdqDFkJhOlN
// SIG // icfhJu83B/LuhamjRqe0/cPvRLDUy+r5YY0KW8nPPE4a
// SIG // s7eTZlwBs2Hvzy69adqw8IyhEI/GW9ne4ZOso5I8L6/5
// SIG // VWLk0hPRnEZ+IVCidyw6pWofZLi/FuhhQWGeSfZlUob6
// SIG // solfNUhlN5d165tEWrJOCDhzWB/QsIecz0fiVGxoxo7P
// SIG // dw6cTvFN3DP8SuDR1ca0OX2h6MH6XfsBriyXLh5DGoLd
// SIG // ozT8E5Ixi1pFrQbJR1GCTTi8W5cJRlTA5vwSt3Lb4Z/f
// SIG // a7mfprzQKv4ySLQazR2qZ8GeNxdYVS2ojH3JB02j/W99
// SIG // ToQBYEIJdHmG2CI2hdBGe07+dnwyOoY7lMdQqsGzUiae
// SIG // YVjy4wR545kV1PjaPgEQeo7v9o9CvN97/Fdv5p5GAy56
// SIG // 87PSdUxGlpmcHyD7QJRJy/7kSzmVTzkU9NEXXc1CW2ew
// SIG // hwDCqA++JX9/JFxTgtlyzdAduUVBq/auCZ9vrzrv248a
// SIG // DKl01T3ZJJ1bjrtxxweWpOyGtXv7/ECmuj1pk5TsMM2Q
// SIG // sIYUuscsCB9r958zHwe2CCvmeGCrmuVTFih2EBeMr4Fz
// SIG // ytlgSCGmGoQuUPw0RU82io1ne5s=
// SIG // End signature block
