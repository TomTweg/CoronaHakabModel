from argparse import ArgumentParser

from consts import Consts
from manager import SimulationManager
from supervisor import LambdaValueSupervisable, Supervisable, Supervisor


def check_args(args):
    if args.input_matrix_path and args.output_matrix_path:
        print("ERROR: Cannot import AND export matrix in the same run!")
        return False


def main():
    parser = ArgumentParser(
        """
    COVID-19 Simulation
    Optional:
        Input path of a pre-generated matrix
        OR
        Output path for the matrix generated now
    Optional:
        Parameters file (see Parameters/parameters_example.py)
    CRITICAL -
        The size of the matrix is not checked when loading an existing file!
        If the size of the population changed - make sure the matrix is appropriate.
    """
    )
    parser.add_argument(
        "-i", "--input-matrix", dest="input_matrix_path", help="npz file path of a pre-generated matrix",
    )
    parser.add_argument(
        "-o", "--output-matrix", dest="output_matrix_path", help="npz file path for the newly-generated matrix",
    )
    parser.add_argument("-p", "--parameters", dest="parameters", help="Parameter file with consts for the simulation")
    args = parser.parse_args()

    if args.parameters:
        consts = Consts.from_file(args.parameters)
    else:
        consts = Consts()

    sm = SimulationManager(
        (
            "Latent",
            "Silent",
            "Asymptomatic",
            "Symptomatic",
            "Deceased",
            "Hospitalized",
            "ICU",
            # "Susceptible",
            "Recovered",
            Supervisable.Sum(
                "Symptomatic", "Asymptomatic", "Latent", "Silent", "ICU", "Hospitalized", name="currently sick"
            ),
            # Supervisable.NewCasesCounter(),
            # Supervisable.GrowthFactor(
            #    Supervisable.Sum("Symptomatic", "Asymptomatic", "Latent", "Silent", "ICU", "Hospitalized"),
            #    Supervisable.NewCasesCounter()),
            # LambdaValueSupervisable("Detected Daily", lambda manager: manager.detected_daily)
            # Supervisable.R0(),
            # Supervisable.Delayed("Symptomatic", 3),
        ),
        input_matrix_path=args.input_matrix_path,
        output_matrix_path=args.output_matrix_path,
        consts=consts,
    )
    print(sm)
    sm.run()
    sm.plot(save=True, max_scale=False)


def compare_simulations_example():
    sm1 = SimulationManager(
        (
            Supervisable.Sum(
                "Symptomatic", "Asymptomatic", "Latent", "Silent", "ICU", "Hospitalized", "Recovered", "Deceased"
            ),
            "Symptomatic",
            "Recovered",
        ),
        consts=Consts(r0=1.5),
    )
    sm1.run()

    sm2 = SimulationManager(
        (
            Supervisable.Sum(
                "Symptomatic", "Asymptomatic", "Latent", "Silent", "ICU", "Hospitalized", "Recovered", "Deceased"
            ),
            "Symptomatic",
            "Recovered",
        ),
        consts=Consts(r0=1.8),
    )
    sm2.run()

    Supervisor.static_plot(
        ((sm1, f"ro = {sm1.consts.r0}:", ("y-", "y--", "y:")), (sm2, f"ro = {sm2.consts.r0}:", ("c-", "c--", "c:"))),
        f"comparing r0 = {sm1.consts.r0} to r0={sm2.consts.r0}",
    )


if __name__ == "__main__":
    main()
