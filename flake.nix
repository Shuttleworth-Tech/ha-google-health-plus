{
  description = "Google Health Plus custom integration for Home Assistant";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python313.withPackages (ps: [
            ps.pip
            ps.setuptools
            ps.wheel
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.ruff
              pkgs.zip
              pkgs.gh
            ];
            shellHook = ''
              if [ ! -e .venv ]; then
                echo "Creating venv and installing test dependencies (first run only)..."
                ${python.interpreter} -m venv .venv
                ./.venv/bin/pip install -q -r requirements_test.txt
              fi
            '';
          };
        });
    };
}
