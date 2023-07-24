from janim import __version__

import janim.config as jconfig
import janim.scene.extract_scene as extract_scene

def main():
    print(f"JAnim \033[32mv{__version__}\033[0m")

    args = jconfig.parse_cli()
    if args.version:
        return
    
    # if args.config:
    #     jconfig.init_customization()
    #     return
    
    config = jconfig.get_configuration()
    scenes = extract_scene.main(args, config)
    
    for scene in scenes:
        scene.run()

if __name__ == '__main__':
    main()
