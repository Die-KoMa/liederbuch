{
  description = "Das Liederbuch der Konferenz der deutschsprachigen Mathematikfachschaften";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
  };

  outputs =
    inputs@{ self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      environment = {
        TEXMFHOME = ".cache";
        TEXMFVAR = ".cache/texmf-var";
        SOURCE_DATE_EPOCH = toString self.lastModified;
      };

      texlive = pkgs.texlive.combine {
        inherit (pkgs.texlive)
          babel
          booktabs
          caption
          collection-fontsrecommended
          collection-langgerman
          colorprofiles
          csquotes
          draftwatermark
          ec
          ellipsis
          eso-pic
          hyperref
          latex-bin
          latexmk
          mathtools
          metafont
          microtype
          multirow
          pdfmanagement-testphase
          pdfx
          scheme-basic
          setspace
          silence
          subfig
          textpos
          titlesec
          todonotes
          truncate
          wasysym
          xkeyval
          xmpincl
          xstring
          ;
      };

      mkDocument =
        name:
        pkgs.stdenvNoCC.mkDerivation rec {
          inherit name;
          src = self;

          allowSubstitutes = false;
          buildInputs = [
            pkgs.coreutils
            pkgs.gawk
            texlive
          ];
          phases = [
            "unpackPhase"
            "buildPhase"
            "installPhase"
          ];
          buildPhase = ''
            runHook preBuild
            export PATH="${pkgs.lib.makeBinPath buildInputs}";
            mkdir -p .cache/texmf-var
            env TEXMFHOME=${environment.TEXMFHOME} \
              TEXMFVAR=${environment.TEXMFVAR} \
              SOURCE_DATE_EPOCH=${environment.SOURCE_DATE_EPOCH} \
              latexmk -interaction=nonstopmode -pdf \
              ${name}.tex
            runHook postBuild
          '';
          installPhase = ''
            runHook preInstall
            cp ${name}.pdf $out
            runHook postInstall
          '';
        };

    in
    {
      packages."${system}" = rec {
        default = liederbuch;
        liederbuch = mkDocument "liederbuch";
      };

      devShells."${system}".default = pkgs.mkShell {
        inherit (environment) TEXMFHOME TEXMFVAR SOURCE_DATE_EPOCH;
        buildInputs = [ texlive ];
      };
    };
}
