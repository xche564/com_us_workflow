#!/usr/bin/env python3
"""
This script generates input files and submission scripts for a complete
AMBER Umbrella Sampling MD workflow including minimization, heating, equilibration, and pulling.
"""
import subprocess

# do this command before running:
# export LD_LIBRARY_PATH=/home/shared_write/gcc/installation/lib64:$LD_LIBRARY_PATH
# export PATH=/home/shared_write/gcc/installation/bin:$PATH
# bash /home/shared_write/gcc/amber_cuda/amber-interactive.sh

# ============================================================================ #
#                        CONFIGURATION PARAMETERS                              #
# ============================================================================ #

# System configuration
TEMP = 298.15                # Target temperature (K)
CUT = 10.0                   # Cutoff distance for nonbonded interactions (Å)
DT_HEAT1 = 0.00005           # Time step for first heating stage (ps)
DT_PRODUCTION = 0.002        # Time step for subsequent stages (ps)

# Files
PARM_FILE = "bdp-btb-acetonitrile.prmtop"  # Topology file "system.parm" 
RST_FILE = "bdp-btb-acetonitrile.inpcrd"      # Input coordinate file  "system.rst"
PDB_FILE = "bdp-btb-acetonitrile.pdb"       # PDB file for atom group extraction "system.pdb"

# Minimization parameters
MIN_MAXCYC = 1000            # Total minimization cycles
MIN_NCYC = 500              # Steepest descent cycles

# Heating parameters
HEAT1_STEPS = 25000          # First heating stage steps (0K to 100K)
HEAT2_STEPS = 100000          # Second heating stage steps (100K to 300K)

# Equilibration parameters
EQUIL_STEPS = 25000          # Equilibration steps

# Pulling parameters
PULL_DIST_START = 3.0        # Initial COM distance (Å)
PULL_DIST_END = 33.0         # Final COM distance (Å)
PULL_FORCE_CONST = 1.0       # Force constant for pulling (kcal/mol·Å²)
PROD_FORCE_CONST = 2.0       # Force constant for production (kcal/mol·Å²)
PULLING_RATE = 0.01          # Pulling rate (nm/ps)

# Production parameters (umbrella sampling for each window)
PROD_STEPS = 1000000         # Production simulation steps
NTWX_PROD = 1000             # Trajectory writing frequency for production

# Output frequency
NTWX_HEAT = 100              # Trajectory writing frequency for heating
NTWX_EQUIL = 100             # Trajectory writing frequency for equilibration
NTWX_PULL = 500              # Trajectory writing frequency for pulling
NTWR_DEFAULT = 1000          # Restart file writing frequency
NTPR_DEFAULT = 100           # Energy info writing frequency

# Groups for pulling (COM calculation)
def extract_first_two_residues_idx_from_pdb(PDB_FILE):
    """
    Extract the indices of the first two residues from the PDB file.
    """
    num_atoms_group1, num_atoms_group2 = 0, 0
    with open(PDB_FILE, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith('TER'):
            if num_atoms_group1 != 0:
                break
            num_atoms_group1 = num_atoms_group2
        if line.startswith('ATOM'):
            num_atoms_group2 += 1
    group1 = list(range(1, num_atoms_group1+1))
    group2 = list(range(num_atoms_group1+1, num_atoms_group2+1))
    # return idx with , separated
    return ",".join(str(i) for i in group1), ",".join(str(i) for i in group2)
GROUP1, GROUP2 = extract_first_two_residues_idx_from_pdb(PDB_FILE)

# ============================================================================ #
#                          TEMPLATE DEFINITIONS                                #
# ============================================================================ #

# Define the input file template for minimization
MIN_TEMPLATE = """Minimize
 &cntrl
  imin=1,  ! Perform an energy minimization.
  ntx=1,   ! Coordinates, but no velocities, will be read
  irest=0, ! no restart
  maxcyc={maxcyc}, ! The maximum number of cycles of minimization
  ncyc={ncyc},   ! cycles of steepest descent before conjugate gradient

  ntb=1,         ! no periodicity is applied and PME is off
  ntp=0,         ! no temperature scaling
  ntpr={ntpr},    ! steps to print the energy
  ntwx=0,      ! steps to write the coordinates
  cut={cut}     ! cutoff distance for nonbonded interactions
 /
"""

# Define the input file template for first heating stage (0K to 100K)
HEAT1_TEMPLATE = """Heating from 0K to 100K
&cntrl
  imin = 0,        ! Single point energy calculation.
  irest = 0,       ! no restart
  ntx = 1,         ! Coordinates, but no velocities, will be read
  tol = 0.0000001, ! Relative geometrical tolerance for coordinate resetting in shake.
  dt = {dt},      ! The time step.
  nstlim = {nstlim},  ! The maximum number of steps.

  ntr = 1,         ! Use position restraints based on the GROUP input
  ntc = 2,         ! Use the SHAKE algorithm to constrain the bonds with hydrogen.
  ntf = 2,         ! bond interactions involving H-atoms omitted as ntc = 2
  cut = {cut},      ! cutoff distance for nonbonded interactions.
  ntt = 3,         ! Use Langevin dynamics with the collision frequency γ given by gamma_ln
  gamma_ln = 1000.0, ! The collision frequency γ.

  ntwx = {ntwx},      ! steps to write the coordinates.
  ntwr = {ntwr},     ! steps to write the restart file.
  ntpr = {ntpr},      ! steps to print the energy.
  ntxo = 2,        ! NetCDF file format of the final coordinates, velocities, and box size

  ig = -1,         ! No random number generator.
  ioutfm = 1       ! Binary NetCDF trajectory format
  nmropt = 1
/
&wt type='TEMP0',
    istep1 = 0,
    istep2 = {nstlim},
    value1 = 0.0,
    value2 = 100.0
/

&wt type='END'
/
Hold system fixed
10.0
RES 1 2
END
END
"""

# Define the input file template for second heating stage (100K to target temp)
HEAT2_TEMPLATE = """Heating from 100K to {temp}K
&cntrl
  imin = 0,        ! Single point energy calculation.
  irest = 1,       ! Restart the simulation, reading coordinates and velocities from a previously saved restart file.
  ntx = 5,         ! Coordinates and velocities will be read
  tol = 0.0000001, ! Relative geometrical tolerance for coordinate resetting in shake.
  dt = {dt},      ! The time step, 2 fs
  nstlim = {nstlim},  ! The maximum number of steps.

  ntb = 1,         ! Use constant volume periodic boundaries
  ntc = 2,         ! Use the SHAKE algorithm to constrain the bonds with hydrogen.
  ntf = 2,         ! bond interactions involving H-atoms omitted as ntc = 2
  cut = {cut},      ! cutoff distance for nonbonded interactions.
  ntt = 3,         ! Use Langevin dynamics with the collision frequency γ given by gamma_ln
  gamma_ln = 1.0,  ! The collision frequency γ.

  ntwx = {ntwx},      ! steps to write the coordinates.
  ntwr = {ntwr},     ! steps to write the restart file.
  ntpr = {ntpr},      ! steps to print the energy.
  ntxo = 2,        ! NetCDF file format of the final coordinates, velocities, and box size
  ioutfm = 1,      ! Binary NetCDF trajectory format

  ig = -1          ! No random number generator.
  nmropt = 1
/
&wt type='TEMP0',
    istep1 = 0,
    istep2 = {nstlim},
    value1 = 100.0,
    value2 = {temp}
/

&wt type='END'
/
Hold system fixed
10.0
RES 1 2
END
END
"""

# Define the input file template for equilibration
EQUIL_TEMPLATE = """NPT Equilibration at {temp}K
 &cntrl
  imin = 0,        ! Single point energy calculation.
  irest = 1,       ! Restart the simulation, reading coordinates and velocities from a previously saved restart file.
  ntx = 5,         ! Coordinates and velocities will be read
  tol = 0.0000001, ! Relative geometrical tolerance for coordinate resetting in shake.
  dt = {dt},      ! The time step, 0.002 ps
  nstlim = {nstlim},  ! The maximum number of steps.

  ntb = 2,         ! constant pressure (default when ntp > 0)
  pres0 = 1.0,     ! pressure (in bar)
  ntp = 1,         ! md with isotropic position scaling
  taup = 5.0,      ! Pressure relaxation time (in ps), when NTP > 0. 
  
  ntc = 2,         ! Use the SHAKE algorithm to constrain the bonds with hydrogen.
  ntf = 2,         ! bond interactions involving H-atoms omitted as ntc = 2
  cut = {cut},      ! cutoff distance for nonbonded interactions.

  tempi = {temp},  ! initial temperature (in K)
  temp0 = {temp},  ! final temperature (in K)
  ntt = 3,         ! Use Langevin dynamics with the collision frequency γ given by gamma_ln
  gamma_ln = 1.0,  ! The collision frequency γ.

  ntwx = {ntwx},      ! steps to write the coordinates.
  ntwr = {ntwr},     ! steps to write the restart file.
  ntpr = {ntpr},      ! steps to print the energy.
  ntxo = 2,        ! NetCDF file format of the final coordinates, velocities, and box size
  ioutfm = 1,      ! Binary NetCDF trajectory format

  ig = -1,          ! No random number generator.
  nmropt = 1,
/
 &wt type='DUMPFREQ', istep1=1000 /
 &wt type='END', /
DISANG=COM_dist.RST
DUMPAVE=equil_dist.dat
LISTIN=POUT
LISTOUT=POUT
/
"""

# Define the input file template for pulling
PULL_TEMPLATE = """NPT Equilibration at {temp}K
&cntrl
  imin = 0,        ! Single point energy calculation.
  irest = 1,       ! Restart the simulation, reading coordinates and velocities from a previously saved restart file.
  ntx = 5,         ! Coordinates and velocities will be read
  tol = 0.0000001, ! Relative geometrical tolerance for coordinate resetting in shake.
  dt = {dt},      ! The time step, 0.002 ps
  nstlim = {nstlim},  ! The maximum number of steps.

  ntb = 2,         ! constant pressure (default when ntp > 0)
  pres0 = 1.0,     ! initial pressure (in bar)
  ntp = 1,         ! md with isotropic position scaling
  taup = 5.0,      ! Pressure relaxation time (in ps), when NTP > 0. 
  
  ntr = 0,         ! no longer using positional restraints.
  ntc = 2,         ! Use the SHAKE algorithm to constrain the bonds with hydrogen.
  ntf = 2,         ! bond interactions involving H-atoms omitted as ntc = 2
  cut = {cut},      ! cutoff distance for nonbonded interactions.

  tempi = {temp},  ! initial temperature (in K)
  temp0 = {temp},  ! final temperature (in K)
  ntt = 3,         ! Use Langevin dynamics with the collision frequency γ given by gamma_ln
  gamma_ln = 1.0,  ! The collision frequency γ.

  ntwx = {ntwx},      ! steps to write the coordinates.
  ntwr = {ntwr},     ! steps to write the restart file.
  ntpr = {ntpr},      ! steps to print the energy.
  ntxo = 2,        ! NetCDF file format of the final coordinates, velocities, and box size
  ioutfm = 1,      ! Binary NetCDF trajectory format

  ig = -1          ! No random number generator.
  nmropt = 1,
  jar = 1,
/
&wt type='DUMPFREQ', istep1=500 /
&wt type='END', /
DISANG=COM_pull.RST
DUMPAVE=pull_dist.dat
LISTIN=POUT
LISTOUT=POUT
/
"""

# Define the input file template for umbrella sampling (production)
PROD_TEMPLATE = """Umbrella-sampling
 &cntrl
  imin=0,
  ntx=1,
  irest=0,
  ntc=2,
  ntf=2,
  tol=0.0000001,
  ntt=3,
  gamma_ln=1.0,
  temp0={temp},
  ig = -1,
  ntpr=1000,
  ntwr={ntwr},
  ntwx={ntwx},
  nstlim={nstlim},
  dt={dt},
  ntb=2,
  cut={cut},
  ioutfm=1,
  ntxo=2,
  nmropt=1,
  ntp=1,
  taup=5.0,
/
 &wt type='DUMPFREQ', istep1=500 /
 &wt type='END', /
DISANG=COM_prod.RST
DUMPAVE=dist.dat
LISTIN=POUT
LISTOUT=POUT
/
/
 &ewald
  skinnb=3.0,
 /
"""

# ============================================================================ #
#                         FUNCTION DEFINITIONS                                 #
# ============================================================================ #
    
def generate_input_file(template, **kwargs):
    """
    Generate an input file by replacing placeholders in the template.
    
    Args:
        template (str): Template string with placeholders
        **kwargs: Keyword arguments to replace placeholders
        
    Returns:
        str: Filled template
    """
    # Replace the placeholders with the provided values
    for key, value in kwargs.items():
        template = template.replace("{"+key+"}", str(value))
    return template


def create_restraint_files(r2, r2a, rk2, rk3, igr1, igr2):
    """
    Create restraint files for equilibration, pulling, and production stages.
    
    Args:
        r2 (float): Initial distance value
        r2a (float): Maximum distance value for pulling
        rk2 (float): Force constant for pulling
        rk3 (float): Force constant for production
        igr1 (str): Atom group 1 for COM calculation
        igr2 (str): Atom group 2 for COM calculation
    """
    # Define buffer distance for equilibration
    r1 = r2 - 1000
    r4 = r2 + 1000
    
    # Create the script with user input variables
    disang_equi = f"""
&rst
iat=-1,-1,
r1={r1},
r2={r2},
r3={r2},
r4={r4},
rk2={rk2},
rk3={rk2},
igr1={igr1},
igr2={igr2},
/
"""

    disang_pull = f"""
&rst
iat=-1,-1,
r2={r2},
rk2={rk2},
r2a={r2a},
igr1={igr1},
igr2={igr2},
/
"""

    disang_prod = f"""
&rst
iat=-1,-1,
r1={r1},
r2=dishere,
r3=dishere,
r4={r4},
rk2={rk3},
rk3={rk3},
igr1={igr1},
igr2={igr2},
/
"""

    # Write restraint files
    with open("COM_dist.RST", "w") as f:
        f.write(disang_equi)

    with open("COM_pull.RST", "w") as f:
        f.write(disang_pull)

    with open("COM_prod.RST", "w") as f:
        f.write(disang_prod)


def create_submission_script(parm_file, rst_file):
    """
    Create a submission script for running the AMBER simulations.
    
    Args:
        parm_file (str): Topology file name
        rst_file (str): Input coordinate file name
        
    Returns:
        str: Submission script content
    """
    script = f"""#!/bin/bash
#SBATCH --time=24:00:00
#SBATCH --partition=day-long
#SBATCH --nodes=1
#SBATCH --mem=5G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --exclude=node1
#SBATCH --gres=gpu:1
echo $HOSTNAME

export LD_LIBRARY_PATH=/home/shared_write/gcc/installation/lib64:$LD_LIBRARY_PATH
export PATH=/home/shared_write/gcc/installation/bin:$PATH
bash /home/shared_write/gcc/amber_cuda/amber-interactive.sh

#--------------------------------------------------------------#

pmemd.cuda -O -i min.in -c {rst_file} -p {parm_file} -r min.rst -x min.nc -o min.out -inf min.info
pmemd.cuda -O -i heat1.in -o heat1.out -p {parm_file} -c min.rst -r heat1.rst -x heat1.nc -ref min.rst
pmemd.cuda -O -i heat2.in -o heat2.out -p {parm_file} -c heat1.rst -r heat2.rst -x heat2.nc -ref heat1.rst
pmemd.cuda -O -i equil.in -o equil.out -p {parm_file} -c heat2.rst -r equil.rst -x equil.nc -inf equil.info
pmemd.cuda -O -i pull.in -o pull.out -p {parm_file} -c equil.rst -r pull.rst -x pull.nc -inf pull.info
"""
    return script


def submit_job(script_path):
    """
    Submit the job to the scheduler.
    
    Args:
        script_path (str): Path to the submission script
    """
    subprocess.run(["sbatch", script_path])


def main():
    """Main function to generate all files and submit the job."""
    # Calculate number of steps for pulling based on rate and distance
    pulling_steps = int((PULL_DIST_END - PULL_DIST_START) * 0.1 / (PULLING_RATE * DT_PRODUCTION))
    
    # Generate the input files
    min_input = generate_input_file(
        MIN_TEMPLATE, 
        maxcyc=MIN_MAXCYC, 
        ncyc=MIN_NCYC, 
        cut=CUT, 
        ntpr=NTPR_DEFAULT
    )
    
    heat1_input = generate_input_file(
        HEAT1_TEMPLATE, 
        dt=DT_HEAT1, 
        nstlim=HEAT1_STEPS, 
        cut=CUT, 
        ntwx=NTWX_HEAT, 
        ntwr=NTWR_DEFAULT, 
        ntpr=NTPR_DEFAULT
    )
    
    heat2_input = generate_input_file(
        HEAT2_TEMPLATE, 
        temp=TEMP, 
        dt=DT_PRODUCTION, 
        nstlim=HEAT2_STEPS, 
        cut=CUT, 
        ntwx=NTWX_HEAT, 
        ntwr=NTWR_DEFAULT, 
        ntpr=NTPR_DEFAULT
    )
    
    equil_input = generate_input_file(
        EQUIL_TEMPLATE, 
        temp=TEMP, 
        dt=DT_PRODUCTION, 
        nstlim=EQUIL_STEPS, 
        cut=CUT, 
        ntwx=NTWX_EQUIL, 
        ntwr=NTWR_DEFAULT, 
        ntpr=NTPR_DEFAULT
    )
    
    pull_input = generate_input_file(
        PULL_TEMPLATE, 
        temp=TEMP, 
        dt=DT_PRODUCTION, 
        nstlim=pulling_steps, 
        cut=CUT, 
        ntwx=NTWX_PULL, 
        ntwr=NTWR_DEFAULT, 
        ntpr=NTPR_DEFAULT
    )
    
    prod_input = generate_input_file(
        PROD_TEMPLATE, 
        temp=TEMP, 
        dt=DT_PRODUCTION, 
        nstlim=PROD_STEPS, 
        cut=CUT, 
        ntwx=NTWX_PROD, 
        ntwr=NTWR_DEFAULT
    )

    # Write the input files to disk
    with open('min.in', 'w') as f:
        f.write(min_input)
    with open('heat1.in', 'w') as f:
        f.write(heat1_input)
    with open('heat2.in', 'w') as f:
        f.write(heat2_input)
    with open('equil.in', 'w') as f:
        f.write(equil_input)
    with open('pull.in', 'w') as f:
        f.write(pull_input)
    with open('prod.in', 'w') as f:
        f.write(prod_input)

    # Create restraint files
    create_restraint_files(
        r2=PULL_DIST_START,
        r2a=PULL_DIST_END,
        rk2=PULL_FORCE_CONST,
        rk3=PROD_FORCE_CONST,
        igr1=GROUP1,
        igr2=GROUP2
    )

    # Generate and write the submission script
    submission_script = create_submission_script(PARM_FILE, RST_FILE)
    with open("amber.sh", "w") as f:
        f.write(submission_script)

    # Submit the job
    print("Job files prepared. Submission script created as 'amber.sh'.")
    submit_decision = input("Do you want to submit the job now? (y/n): ")
    if submit_decision.lower() == 'y':
        submit_job("./amber.sh")
        print("Job submitted.")
    else:
        print("Job not submitted. Run 'sbatch amber.sh' to submit manually.")


if __name__ == "__main__":
    main()


