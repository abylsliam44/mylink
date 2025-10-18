from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json
from typing import Dict

from app.db.session import get_db
from app.models.response import CandidateResponse, ResponseStatus
from app.models.chat import SenderType
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/chat/{response_id}")
async def chat_websocket(
    websocket: WebSocket,
    response_id: UUID
):
    """
    WebSocket endpoint for candidate chat
    """
    await websocket.accept()
    
    # Store connection
    connection_key = str(response_id)
    active_connections[connection_key] = websocket
    
    try:
        # Get database session
        async for db in get_db():
            # Verify response exists
            result = await db.execute(
                select(CandidateResponse).where(CandidateResponse.id == response_id)
            )
            response = result.scalar_one_or_none()
            
            if not response:
                await websocket.send_json({
                    "type": "error",
                    "message": "Response not found"
                })
                await websocket.close()
                return
            
            # Update response status to in_chat
            response.status = ResponseStatus.IN_CHAT
            await db.flush()
            
            # Create or get chat session
            session_result = await db.execute(
                select(CandidateResponse).where(CandidateResponse.id == response_id)
            )
            response_obj = session_result.scalar_one()
            
            if not response_obj.chat_session:
                chat_session = await ChatService.create_session(response_id, db)
            else:
                chat_session = response_obj.chat_session
            
            # Get bot questions
            questions = await ChatService.get_bot_questions()
            current_question_index = 0
            
            # Send first question
            first_question = questions[current_question_index]
            await ChatService.add_message(
                chat_session.id,
                SenderType.BOT,
                first_question,
                db
            )
            await db.commit()
            
            await websocket.send_json({
                "type": "bot_message",
                "message": first_question,
                "question_index": current_question_index
            })
            
            # Listen for candidate messages
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                candidate_message = message_data.get("message", "")
                
                if not candidate_message:
                    continue
                
                # Save candidate message
                await ChatService.add_message(
                    chat_session.id,
                    SenderType.CANDIDATE,
                    candidate_message,
                    db
                )
                await db.commit()
                
                # Process answer
                process_result = await ChatService.process_candidate_answer(
                    response_id,
                    current_question_index,
                    candidate_message,
                    db
                )
                
                if not process_result.get("continue", False):
                    # Chat should end
                    approved = process_result.get("approved", False)
                    reason = process_result.get("reason", "Чат завершен")
                    
                    # Finalize response
                    await ChatService.finalize_response(
                        response_id,
                        approved,
                        reason,
                        db
                    )
                    
                    # End session
                    await ChatService.end_session(chat_session.id, db)
                    await db.commit()
                    
                    # Send final message
                    if approved:
                        final_message = "Спасибо за ответы! Ваша заявка одобрена. Работодатель свяжется с вами."
                    else:
                        final_message = f"Спасибо за ваше время. К сожалению, {reason}"
                    
                    await ChatService.add_message(
                        chat_session.id,
                        SenderType.BOT,
                        final_message,
                        db
                    )
                    await db.commit()
                    
                    await websocket.send_json({
                        "type": "bot_message",
                        "message": final_message
                    })
                    
                    await websocket.send_json({
                        "type": "chat_ended",
                        "approved": approved,
                        "reason": reason
                    })
                    
                    break
                else:
                    # Continue to next question
                    current_question_index += 1
                    
                    if current_question_index < len(questions):
                        next_question = questions[current_question_index]
                        
                        await ChatService.add_message(
                            chat_session.id,
                            SenderType.BOT,
                            next_question,
                            db
                        )
                        await db.commit()
                        
                        await websocket.send_json({
                            "type": "bot_message",
                            "message": next_question,
                            "question_index": current_question_index
                        })
            
            break  # Exit the async for loop
    
    except WebSocketDisconnect:
        # Client disconnected
        if connection_key in active_connections:
            del active_connections[connection_key]
    
    except Exception as e:
        # Handle errors
        await websocket.send_json({
            "type": "error",
            "message": f"An error occurred: {str(e)}"
        })
        if connection_key in active_connections:
            del active_connections[connection_key]
        await websocket.close()

