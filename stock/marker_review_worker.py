"""Worker loaded by the installed Marker interpreter; no optional LLM processors."""
import ipaddress
import json
import socket
import sys
from pathlib import Path


def install_network_guard():
    original_resolve=socket.getaddrinfo
    def local_resolve(host,*args,**kwargs):
        if host is not None:
            try: local=ipaddress.ip_address(host).is_loopback
            except ValueError: local=host in ('localhost',b'localhost')
            if not local: raise RuntimeError('Review blocks external DNS and downloads')
        return original_resolve(host,*args,**kwargs)
    socket.getaddrinfo=local_resolve
    def wrap(original):
        def guarded(sock,address,*args,**kwargs):
            if sock.family in (socket.AF_INET,socket.AF_INET6):
                host=address[0]
                try: local=ipaddress.ip_address(host).is_loopback
                except ValueError: local=host=='localhost'
                if not local: raise RuntimeError('Review blocks non-loopback inference and downloads')
            return original(sock,address,*args,**kwargs)
        return guarded
    socket.socket.connect=wrap(socket.socket.connect)
    socket.socket.connect_ex=wrap(socket.socket.connect_ex)


def main():
    install_network_guard()
    source,output=map(Path,sys.argv[1:3])
    from importlib.metadata import version
    versions={p:version(p) for p in ('marker-pdf','surya-ocr')}
    (output/'versions.json').write_text(json.dumps(versions,indent=2))
    from marker.config.parser import ConfigParser
    original=ConfigParser.generate_config_dict
    def local_config(self):
        config=original(self)
        config.update(json.loads((output/'config.json').read_text()))
        config['use_llm']=False
        return config
    ConfigParser.generate_config_dict=local_config
    ConfigParser.get_llm_service=lambda self:None
    # Disable all auto-starts after settings/local.env loading as well. Existing
    # services remain shared and are never stopped or reconfigured by this tool.
    from surya.settings import settings
    settings.SURYA_INFERENCE_AUTOSTART=False
    settings.FAST_LAYOUT_SERVER_AUTOSTART=False
    settings.OCR_ERROR_SERVER_AUTOSTART=False
    settings.DETECTOR_SERVER_AUTOSTART=False
    settings.SURYA_INFERENCE_BACKEND='llamacpp'
    from marker.scripts.convert_single import convert_single_cli
    sys.argv=[sys.argv[0],str(source),'--output_dir',str(output),'--output_format','markdown']
    convert_single_cli()


if __name__=='__main__':
    main()
