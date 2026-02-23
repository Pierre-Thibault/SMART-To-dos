{
  description = "SMART Goals Tracker - FastAPI dashboard";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        pythonPkgs = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPkgs.fastapi
            pythonPkgs.uvicorn
            pythonPkgs.pyyaml
            pythonPkgs.pytest
            pythonPkgs.pytest-cov
            pythonPkgs.httpx
          ];

          shellHook = ''
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
            echo "🎯 SMART Goals Tracker"
            echo "Lancer: uvicorn app.main:app --reload"
            echo "GOALS_VAULT_PATH=./sample_vault par défaut"
          '';
        };
      }
    );
}
