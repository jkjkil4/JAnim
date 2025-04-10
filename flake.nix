{
  description = "Hello world flake using uv2nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        inherit (nixpkgs) lib;
        pkgs = import nixpkgs { inherit system; };

        # Use Python 3.13 from nixpkgs
        python = pkgs.python313;
      in {
        # This example provides two different modes of development:
        # - Impurely using uv to manage virtual environments
        # - Pure development using uv2nix to manage virtual environments
        devShells.default =
          # It is of course perfectly OK to keep using an impure virtualenv workflow and only use uv2nix to build packages.
          # This devShell simply adds Python and undoes the dependency leakage done by Nixpkgs Python infrastructure.
          pkgs.mkShell rec {
            buildInputs = (with pkgs; pkgs.lib.optionals pkgs.stdenv.isLinux [
            ]);
            packages = with pkgs;
              [
                uv
                ffmpeg
                typst
                miniserve
              ] ++ [ python ];

            env = {
              # Prevent uv from managing Python downloads
              UV_PYTHON_DOWNLOADS = "never";
              # Force uv to use nixpkgs Python interpreter
              UV_PYTHON = python.interpreter;
            } // lib.optionalAttrs pkgs.stdenv.isLinux {
              # Python libraries often load native shared objects using dlopen(3).
              # Setting LD_LIBRARY_PATH makes the dynamic library loader aware of libraries without using RPATH for lookup.
              LD_LIBRARY_PATH =
                lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1;
            };
            shellHook = ''
              unset PYTHONPATH
              export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${builtins.toString (pkgs.lib.makeLibraryPath buildInputs)}"
            '';
          };
      });
}
