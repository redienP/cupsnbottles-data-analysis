#!/bin/bash
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=1
#SBATCH --partition=gpu
#SBATCH --mail-user=jkonkol@techfak.uni-bielefeld.de
#SBATCH --mail-type=END
export CPU_AVAIL=4
chmod 777 preprocessing_job.sh
srun preprocessing_job.sh
