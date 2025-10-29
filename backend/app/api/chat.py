from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
import json
from typing import Dict, List

from app.db.session import get_db
from app.models.response import CandidateResponse, ResponseStatus
from app.models.chat import SenderType, ChatMessage, ChatSession
from app.services.chat_service import ChatService
from app.services.interview_service import interview_service

router = APIRouter(tags=["Chat"])

# Store active WebSocket connections (one per response_id)
# Format: {response_id: websocket}
active_connections: Dict[str, WebSocket] = {}


async def send_message_to_candidate(response_id: UUID, message: str, message_type: str = "bot_message"):
    """Send a message to a candidate via WebSocket if they are connected"""
    connection_key = str(response_id)
    if connection_key in active_connections:
        ws = active_connections[connection_key]
        try:
            await ws.send_json({
                "type": message_type,
                "message": message
            })
            return True
        except Exception as e:
            print(f"Failed to send message to {response_id}: {e}")
            # Remove dead connection
            if connection_key in active_connections:
                del active_connections[connection_key]
            return False
    return False


@router.websocket("/ws/chat/{response_id}")
async def chat_websocket(
    websocket: WebSocket,
    response_id: UUID
):
    """
    WebSocket endpoint for AI-powered candidate interview
    """
    await websocket.accept()

    # Store connection and disconnect any previous connection (single-session enforcement)
    connection_key = str(response_id)
    
    # If there's already an active connection, disconnect it
    if connection_key in active_connections:
        old_ws = active_connections[connection_key]
        try:
            await old_ws.send_json({
                "type": "disconnected",
                "message": "Новое подключение обнаружено. Чат открыт на другом устройстве."
            })
            await old_ws.close()
        except:
            pass  # Old connection might already be closed
    
    active_connections[connection_key] = websocket

    interview_questions: List[Dict] = []
    current_question_index = 0

    try:
        # Get database session
        async for db in get_db():
            # Verify response exists and eagerly load chat_session
            result = await db.execute(
                select(CandidateResponse)
                .options(selectinload(CandidateResponse.chat_session))
                .where(CandidateResponse.id == response_id)
            )
            response = result.scalar_one_or_none()

            if not response:
                await websocket.send_json({
                    "type": "error",
                    "message": "Response not found"
                })
                await websocket.close()
                return

            # Check if interview already has questions (resume chat)
            # Check if mismatch_analysis exists and has questions (with fallback for missing columns)
            mismatch_analysis = getattr(response, 'mismatch_analysis', None)
            dialog_findings = getattr(response, 'dialog_findings', None)
            
            has_existing_questions = (
                mismatch_analysis and 
                isinstance(mismatch_analysis, dict) and
                mismatch_analysis.get("questions")
            )
            
            if has_existing_questions:
                # Resume existing interview
                interview_questions = mismatch_analysis.get("questions", [])
                current_question_index = len(dialog_findings.get("answers", [])) if dialog_findings else 0

                # Send next question if available
                if current_question_index < len(interview_questions):
                    next_question = interview_questions[current_question_index]
                    question_text = next_question.get("question_text", "")

                    # Create or get chat session
                    if not response.chat_session:
                        chat_session = await ChatService.create_session(response_id, db)
                        response.chat_session = chat_session
                        await db.commit()  # Commit immediately to persist chat_session
                    else:
                        chat_session = response.chat_session

                    await ChatService.add_message(
                        chat_session.id,
                        SenderType.BOT,
                        question_text,
                        db
                    )
                    await db.commit()

                    await websocket.send_json({
                        "type": "bot_message",
                        "message": question_text,
                        "question_index": current_question_index,
                        "total_questions": len(interview_questions)
                    })
                else:
                    # Interview already completed - but don't close connection yet
                    # Just inform the user
                    await websocket.send_json({
                        "type": "info",
                        "message": "Интервью уже завершено. Ожидаем решения HR."
                    })
                    await db.commit()
            else:
                # Start new interview
                # Update response status to in_chat
                response.status = ResponseStatus.IN_CHAT
                await db.flush()

                print(f"🚀 Starting new interview for response {response_id}")
                # Start interview with AI analysis
                interview_result = await interview_service.start_interview(
                    response_id=response_id,
                    db=db,
                    language=getattr(response, 'language_preference', None) or "ru"
                )
                print(f"🎯 Interview result received: {len(interview_result.get('questions', []))} questions")

                interview_questions = interview_result["questions"]
                current_question_index = 0
                print(f"📊 Total questions: {len(interview_questions)}")

                # Create or get chat session
                if not response.chat_session:
                    chat_session = await ChatService.create_session(response_id, db)
                    response.chat_session = chat_session
                    await db.commit()  # Commit immediately to persist chat_session
                else:
                    chat_session = response.chat_session

                # Send first question
                if interview_questions:
                    first_question = interview_questions[0]
                    question_text = first_question.get("question_text", "")

                    await ChatService.add_message(
                        chat_session.id,
                        SenderType.BOT,
                        question_text,
                        db
                    )
                    await db.commit()

                    print(f"📤 Sending first question to WebSocket: {question_text[:50]}...")
                    await websocket.send_json({
                        "type": "bot_message",
                        "message": question_text,
                        "question_index": current_question_index,
                        "total_questions": len(interview_questions),
                        "progress": f"Вопрос {current_question_index + 1} из {len(interview_questions)}"
                    })
                    print(f"✅ First question sent successfully")
                else:
                    # No questions generated - inform user but keep connection open
                    print(f"ℹ️  No questions generated, sending info message")
                    await websocket.send_json({
                        "type": "info",
                        "message": interview_result.get("closing_message", "Все данные уже заполнены. Ожидаем решения HR."),
                    })
                    await db.commit()
                    print(f"✅ Info message sent")

            # Listen for candidate messages
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                msg_type = message_data.get("type", "message")
                
                # Handle cancel/exit
                if msg_type == "cancel" or msg_type == "exit":
                    await websocket.send_json({
                        "type": "chat_cancelled",
                        "message": "Собеседование отменено. Вы можете вернуться позже."
                    })
                    break
                
                # Handle pause (just acknowledge, resume will reconnect)
                if msg_type == "pause":
                    await websocket.send_json({
                        "type": "chat_paused",
                        "message": "Собеседование приостановлено. Вы можете продолжить в любое время."
                    })
                    break

                candidate_message = message_data.get("message", "")

                if not candidate_message:
                    continue

                # Create or get chat session (in case it wasn't created earlier)
                if not response.chat_session:
                    chat_session = await ChatService.create_session(response_id, db)
                    response.chat_session = chat_session
                    await db.commit()  # Commit immediately to persist chat_session

                # Save candidate message
                await ChatService.add_message(
                    response.chat_session.id,
                    SenderType.CANDIDATE,
                    candidate_message,
                    db
                )
                await db.commit()

                # Process answer with InterviewService
                if current_question_index < len(interview_questions):
                    question_id = interview_questions[current_question_index].get("id")
                    process_result = await interview_service.process_answer(
                        response_id=response_id,
                        question_id=question_id,
                        answer_text=candidate_message,
                        db=db
                    )

                    # Calculate updated relevance score after each answer
                    relevance_result = await interview_service.calculate_relevance(
                        response_id=response_id,
                        db=db
                    )

                    # Check if we should continue or end
                    if current_question_index + 1 >= len(interview_questions):
                        # Last question answered - finalize interview
                        final_result = await interview_service.finalize_interview(
                            response_id=response_id,
                            db=db
                        )

                        # Send final message
                        closing_msg = interview_questions[-1].get("closing_message", "") if interview_questions else ""
                        if not closing_msg:
                            if final_result["verdict"] == "подходит":
                                closing_msg = "Спасибо за ответы! Ваша заявка одобрена. Работодатель свяжется с вами."
                            else:
                                closing_msg = f"Спасибо за ваше время. {final_result.get('summary', {}).get('one_liner', 'Интервью завершено.')}"

                        await ChatService.add_message(
                            response.chat_session.id,
                            SenderType.BOT,
                            closing_msg,
                            db
                        )
                        await db.commit()

                        await websocket.send_json({
                            "type": "bot_message",
                            "message": closing_msg
                        })

                        await websocket.send_json({
                            "type": "chat_ended",
                            "approved": final_result["verdict"] == "подходит",
                            "final_score": final_result["final_score"],
                            "verdict": final_result["verdict"],
                            "completed": True
                        })

                        break
                    else:
                        # Continue to next question
                        current_question_index += 1
                        next_question = interview_questions[current_question_index]
                        next_question_text = next_question.get("question_text", "")

                        await ChatService.add_message(
                            response.chat_session.id,
                            SenderType.BOT,
                            next_question_text,
                            db
                        )
                        await db.commit()

                        await websocket.send_json({
                            "type": "bot_message",
                            "message": next_question_text,
                            "question_index": current_question_index,
                            "total_questions": len(interview_questions),
                            "progress": f"Вопрос {current_question_index + 1} из {len(interview_questions)}",
                            "current_score": relevance_result["relevance_score"]
                        })
            
            # Keep DB session alive until WebSocket closes
            break

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

