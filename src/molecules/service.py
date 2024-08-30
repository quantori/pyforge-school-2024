import csv
from functools import lru_cache

from fastapi import UploadFile

from src.exception import UnknownIdentifierException
from src.molecules.exception import (
    DuplicateSmilesException,
    InvalidCsvHeaderColumnsException,
    InvalidSmilesException,
)
from src.molecules.repository import (
    MoleculeRepository,
    get_molecule_repository,
)
from src.molecules.schema import MoleculeRequest, MoleculeResponse
from src.molecules.utils import (
    get_chem_molecule_from_smiles_or_raise_exception,
    is_valid_smiles,
)
from src.database import get_session_factory


class MoleculeService:
    required_columns = {"smiles", "name"}

    def __init__(self, repository: MoleculeRepository, session_factory):
        self._repository = repository
        self._session_factory = session_factory

    def exists_by_id(self, obj_id: int):
        """
        Check if a molecule with the given id exists.
        :param obj_id: molecule id
        :return: True if the molecule exists, False otherwise
        """
        with self._session_factory() as session:
            return self._repository.find_by_id(obj_id, session) is not None

    def find_by_id(self, obj_id: int):
        """
        Find a molecule by its id. Calls exists_by_id to check if the molecule exists, resulting in two database calls.
        Not vert impressive, but I am trying to keep it simple.

        :param obj_id:  molecule id
        :return: found molecule
        :raises UnknownIdentifierException: if the molecule with the given id does not exist
        """
        with self._session_factory() as session:
            if not self.exists_by_id(obj_id):
                raise UnknownIdentifierException(obj_id)
            mol = self._repository.find_by_id(obj_id, session)
            return mol.to_response()

    def save(self, molecule_request: MoleculeRequest):
        """
        Simply save a new molecule to the database. If the smiles is not unique, the database will raise an exception.

        :param molecule_request: Molecule data
        :return: Saved molecule
        """
        with self._session_factory() as session:
            same_smiles = self._repository.filter(
                session, smiles=molecule_request.smiles
            )
            if len(same_smiles) > 0:
                raise DuplicateSmilesException(molecule_request.smiles)
            mol = self._repository.save(session, molecule_request.model_dump())
            return mol.to_response()

    def update(self, obj_id: int, molecule_request: MoleculeRequest):
        """
        Update a molecule with the given id.
        This is suitable for put request

        :param obj_id: Identifier of the molecule to be updated
        :param molecule_request: New data for the molecule
        :return: Updated molecule
        :raises UnknownIdentifierException: if the molecule with the given id does not exist
        """
        with self._session_factory() as session:
            if not self.exists_by_id(obj_id):
                raise UnknownIdentifierException(obj_id)

            same_smiles = self._repository.filter(
                smiles=molecule_request.smiles, session=session
            )
            if len(same_smiles) > 0 and same_smiles[0].molecule_id != obj_id:
                raise DuplicateSmilesException(molecule_request.smiles)

            mol = self._repository.update(
                session, obj_id, molecule_request.model_dump()
            )
            return mol.to_response()

    def find_all(self, page: int = 0, page_size: int = 1000):
        """
        Find all molecules in the database. Can be paginated. Default page size is 1000.

        :param page: Zero indexed page number, default is 0
        :param page_size: Items per page, default is 1000
        :return: List of all molecules
        """
        with self._session_factory() as session:
            find_all = self._repository.find_all(
                session=session, page=page, page_size=page_size
            )
            return [molecule.to_response() for molecule in find_all]

    def delete(self, obj_id: int) -> bool:
        """
        Delete a molecule with the given id. If the molecule does not exist, raise an exception.

        :param obj_id: Identifier of the molecule to be deleted
        :return: True
        :raises UnknownIdentifierException: if the molecule with the given id does not exist
        """
        with self._session_factory() as session:
            if not self.exists_by_id(obj_id):
                raise UnknownIdentifierException(obj_id)
            return self._repository.delete(session, obj_id)

    def get_substructures(self, smiles: str) -> list[MoleculeResponse]:
        """
        Find all molecules that are substructures of the given smiles.

        :param smiles: smiles string
        :return: List of molecules that are substructures of the given smiles
        :raises InvalidSmilesException: if the smiles does not represent a valid molecule
        """

        with self._session_factory() as session:
            mol = get_chem_molecule_from_smiles_or_raise_exception(smiles)
            find_all = self._repository.find_all(session)
            substructures = []
            for molecule in find_all:
                if mol.HasSubstructMatch(molecule.to_chem()):
                    substructures.append(molecule.to_response())

            return substructures

    def get_is_substructure_of(self, smiles: str) -> list[MoleculeResponse]:
        """
        Find all the molecules that this molecule is a substructure of.

        :param smiles:
        :return:  List of molecules that this molecule is a substructure of.
        :raises InvalidSmilesException: if the smiles does not represent a valid molecule
        """
        with self._session_factory() as session:
            mol = get_chem_molecule_from_smiles_or_raise_exception(smiles)
            find_all = self._repository.find_all(session)
            is_substructure_of = []
            for molecule in find_all:
                if molecule.to_chem().HasSubstructMatch(mol):
                    is_substructure_of.append(molecule.to_response())
            return is_substructure_of

    def process_csv_file(self, file: UploadFile):
        """
        Process a CSV file and add molecules to the database. The CSV file must have the following columns:

        - smiles
        - name

        Lines that have incorrect format, missing smiles string or invalid smiles string are ignored, and the valid
        molecules are added to the database.

        :return: Number of molecules added successfully
        """

        contents = file.file.read().decode("utf-8")
        csv_reader = csv.DictReader(contents.splitlines())

        self.__validate_csv_header_columns(set(csv_reader.fieldnames))

        number_of_molecules_added = 0

        for row in csv_reader:
            try:
                if not is_valid_smiles(row["smiles"]):
                    raise InvalidSmilesException(row["smiles"])
                self.save(MoleculeRequest(smiles=row["smiles"], name=row["name"]))
                number_of_molecules_added += 1
            except Exception as e:
                """
                We are ignoring the exception and continuing to the next line. It is not important
                whole file to be valid, we just want to add as many molecules as possible.
                """
                print(e)
        return number_of_molecules_added

    def __validate_csv_header_columns(self, columns: set[str]):
        """

        :param columns:
        :return:
        :raises InvalidCsvHeaderColumnsException:
        """
        missing_columns = self.required_columns - columns
        if missing_columns:
            raise InvalidCsvHeaderColumnsException(missing_columns)


@lru_cache
def get_molecule_service():
    return MoleculeService(get_molecule_repository(), get_session_factory())
