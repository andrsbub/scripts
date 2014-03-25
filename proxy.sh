if [ "$1" == "off" ]
then
   unset http_proxy
   unset https_proxy
   echo "Proxy disabled"
else
   case "$1" in
      pa*) http_proxy="http://palzproxy1.lsi.com:9480" ;;
      ge*) http_proxy="http://geezproxy1.lsi.com:9400" ;;
      *)   http_proxy="http://enbzproxy1.lsi.com:9480" ;;
   esac
   export http_proxy
   export https_proxy=$http_proxy
   echo "Proxy $http_proxy enabled"
fi
