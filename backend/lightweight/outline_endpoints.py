"""
Outline API Endpoints - Add to api.py

Insert after workspace settings endpoints
"""

@app.post("/api/workspace/{workspace_id}/upload-outline")
async def upload_outline(workspace_id: str, outline: Dict[str, Any]):
    """Upload custom thesis outline."""
    try:
        from services.outline_parser import outline_parser
        
        success = outline_parser.save_outline(workspace_id, outline)
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid outline structure")
        
        return {
            "success": True,
            "workspace_id": workspace_id,
            "chapters": len(outline.get("chapters", []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{workspace_id}/outline")
async def get_outline(workspace_id: str):
    """Get thesis outline for workspace."""
    try:
        from services.outline_parser import outline_parser
        
        outline = outline_parser.load_outline(workspace_id)
        
        return {
            "workspace_id": workspace_id,
            "outline": outline
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outlines/templates")
async def list_outline_templates():
    """List available outline templates."""
    try:
        from services.outline_parser import outline_parser
        
        templates = outline_parser.list_templates()
        
        return {
            "templates": templates
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/outlines/templates/{template_id}")
async def get_outline_template(template_id: str):
    """Get specific outline template."""
    try:
        from services.outline_parser import outline_parser
        
        outline = outline_parser.get_default_outline(template_id)
        
        return {
            "template_id": template_id,
            "outline": outline
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
