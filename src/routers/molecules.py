from fastapi import APIRouter, Query, HTTPException
from src.db.molecule import (
    get_filtered,
    get_all,
    find_by_id,
    create,
    update_by_id,
    delete_by_id,
)
from src.models.molecule import RequestMolecule, ResponseMolecule

router = APIRouter()


@router.get(
    "",
    summary="Get all molecules",
    description="""Get all molecules or seach for all
                containing a specfied substructre""",
)
async def get_all_molecules(
    substructre: str | None = Query(None, example="CO")
) -> list[ResponseMolecule]:
    if substructre:
        filtered_molecules = get_filtered(substructre)
        return [ResponseMolecule.model_validate(m) for m in filtered_molecules]
    molecules = get_all()
    return [ResponseMolecule.model_validate(m) for m in molecules]


@router.get(
    "/{molecule_id}",
    summary="Get molecule by id",
    description="Get the molecule with the specifed id",
    response_model_exclude=422
)
async def get_molecule_by_id(molecule_id: int) -> ResponseMolecule:
    molecule = find_by_id(molecule_id)
    if not molecule:
        raise HTTPException(
            status_code=404, detail=f"Molecule not found by id: {molecule_id}"
        )
    return ResponseMolecule.model_validate(molecule)


@router.post(
    "",
    status_code=201,
    summary="Create a molecule",
    description="Create a molecule with specified SMILE",
)
async def create_molecule(request: RequestMolecule) -> ResponseMolecule:
    created_molecule = create(request)
    return ResponseMolecule.model_validate(created_molecule)


@router.put(
    "/{molecule_id}",
    summary="Update a molecule",
    description="""Replace the molecule with specifed id with a new one
                that has the same id but new SMILE""",
)
async def update_molecule_by_id(
    molecule_id: int, request: RequestMolecule
) -> ResponseMolecule:
    updated_molecule = update_by_id(molecule_id, request)
    if not updated_molecule:
        raise HTTPException(
            status_code=404, detail=f"Molecule not found by id: {molecule_id}"
        )
    return ResponseMolecule.model_validate(updated_molecule)


@router.delete(
    "/{molecule_id}",
    status_code=204,
    summary="Delete a molecule",
    description="Delete the moleclue with the specified id",
)
async def delete_molecule_by_id(molecule_id: int):
    deleted = delete_by_id(molecule_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Molecule not found by id: {molecule_id}"
        )
