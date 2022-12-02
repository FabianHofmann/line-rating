# Dynamic Line Rating with PyPSA-EUR

Workflow and paper for the Dynamic Line Rating project

For installation clone the `PyPSA-EUR` repository into the root directory

```
git clone --branch line-rating git@github.com:PyPSA/pypsa-eur.git
```

and create the dedicated `conda` environment

```
conda env create -f environment.yaml
conda activate line-rating
```

download submodules after cloning:

```
git submodule update --init
```

update submodule with:

```
git submodule update --remote

```

## License

This work is licensed under a [Creative Commons Zero v1.0 Universal](https://creativecommons.org/choose/zero/)
