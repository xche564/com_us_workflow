# Run center-of-mass (COM) umbrella sampling (US) for TPAB-BODIPY system
First obtain BODIPY and TPAB xyz/pdb file. The solvent's .frcmod and .off files downloadeded from http://amber.manchester.ac.uk/ are not all atoms. So we also need to do that for solvent.

# Step 1: Generate separate force field parameters and geometry files
Use antechamber to create AMBER parameters for each solute molecule.
If your structure is in .xyz, first convert to pdb. Also 

>obabel solute.xyz -O solute.pdb

>antechamber -i solute.pdb -fi pdb -o solute.mol2 -fo mol2 -c bcc -s 2

>parmchk2 -i solute.mol2 -f mol2 -o solute.frcmod

Then use tleap to convert the resulting solute.mol2 into an AMBER library file (solute.off):

>tleap -f convert.leap

# Step 2: Pack geometries together
Pack BODIPY, TPAB, and 4600 ACN molecules in a 80x80x80 box

>/home/xuchen/rfmm/packmol/packmol < packmol.inp

# Step 3: Generate topology file 
Reference: https://ambermd.org/tutorials/pengfei/

>tleap -s -f build.leap > build.out

The above steps needs careful .pdb file format corrections to work. Using Autosolvate can avoid those tedious steps, you only need .off and .frcmod files for solvent, .xyz file for the solute complex and a parameter json file (see system/prep/autosolvate/prep_files/). Here, since both BODIPY and TPAB molecules contain a boron (B) atom, and the parameter for the B atom is not available in the Gaff force field, force field fitting is required. For our case, we did force field fitting to generate the parameter files.

>autosolvate boxgen_multicomponent -f boxgen.json

Then you can obtain the inprcrd, pdb, prmtop of the solvated system. 
# Step 4: Minimization, Heating, Equilibration and Pulling Simulation
>python min_heat_equi_pull.py

# Step 5: Restrained MD at each window
>python windows.py

# Step 6: PMF Profile Generation
From the constrained MD simulation, Weighted histogram analysis method (WHAM) was used to calculate PMF profile.
>python pmf.py


