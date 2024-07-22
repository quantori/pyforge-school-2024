from pydantic import BaseModel

BASE_URL = ""


class Link(BaseModel):
    href: str
    rel: str
    type: str


class HATEOASResponse(BaseModel):
    links: dict[str, Link]


class AddMoleculeRequest(BaseModel):
    smiles: str
    molecule_name: str | None = None
    description: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                    "molecule_name": "Aspirin",
                    "description": "Aspirin is in a group of medications called salicylates... so on and so forth."
                }
            ]
        }
    }


class MoleculeResponse(AddMoleculeRequest, HATEOASResponse):
    molecule_id: int
    links: dict[str, Link] = {}

    @staticmethod
    def from_molecule(molecule: 'Molecule') -> 'MoleculeResponse':
        links = {
            "self": Link(
                href=f"{BASE_URL}/molecules/{molecule.molecule_id}",
                rel="self",
                type="GET"
            ),
            "substructure_search": Link(
                href=f"{BASE_URL}/molecules/substructure_search?smiles={molecule.smiles}",
                rel="substructure_search",
                type="GET"
            )
        }

        return MoleculeResponse(molecule_id=molecule.molecule_id, smiles=molecule.smiles,
                                molecule_name=molecule.molecule_name, description=molecule.description, links=links)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "molecule_id": 1,
                    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                    "molecule_name": "Aspirin",
                    "description": "Aspirin is in a group of medications called salicylates... so on and so forth."
                }
            ]
        }
    }


class Molecule:
    __next_id = 0

    def __init__(self, smiles: str, molecule_name: str | None = None, description: str | None = None):
        self._molecule_id: int = Molecule.__next_id
        Molecule.__next_id += 1
        self.molecule_name: str = molecule_name
        self.smiles: str = smiles
        self.description: str | None = description

    @property
    def molecule_id(self) -> int:
        return self._molecule_id

    @staticmethod
    def from_add_molecule_request(add_molecule_request: AddMoleculeRequest) -> 'Molecule':
        return Molecule(smiles=add_molecule_request.smiles, molecule_name=add_molecule_request.molecule_name,
                        description=add_molecule_request.description)
