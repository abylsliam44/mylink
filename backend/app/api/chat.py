from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import json
from typing import Dict, List

from app.db.session import get_db
from app.models.response import CandidateResponse, ResponseStatus
from app.models.chat import SenderType, ChatMessage
from app.services.chat_service import ChatService
from app.services.interview_service import interview_service

router = APIRouter(tags=["Chat"])

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/chat/{response_id}")
async def chat_websocket(
    websocket: WebSocket,
    response_id: UUID
):
    """
    WebSocket endpoint for AI-powered candidate interview
    """
    await websocket.accept()

    # Store connection
    connection_key = str(response_id)
    active_connections[connection_key] = websocket

    interview_questions: List[Dict] = []
    current_question_index = 0

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

            # Check if interview already has questions (resume chat)
            if response.mismatch_analysis and response.dialog_findings:
                # Resume existing interview
                interview_questions = response.mismatch_analysis.get("questions", [])
                current_question_index = len(response.dialog_findings.get("answers", []))

                # Send next question if available
                if current_question_index < len(interview_questions):
                    next_question = interview_questions[current_question_index]
                    question_text = next_question.get("question_text", "")

                    # Create or get chat session
                    if not response.chat_session:
                        chat_session = await ChatService.create_session(response_id, db)
                        response.chat_session = chat_session
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
                    # Interview already completed
                    await websocket.send_json({
                        "type": "chat_ended",
                        "message": "Интервью уже завершено",
                        "completed": True
                    })
                    return
            else:
                # Start new interview
                # Update response status to in_chat
                response.status = ResponseStatus.IN_CHAT
                await db.flush()

                # Start interview with AI analysis
                interview_result = await interview_service.start_interview(
                    response_id=response_id,
                    db=db,
                    language=response.language_preference or "ru"
                )

                interview_questions = interview_result["questions"]
                current_question_index = 0

                # Create or get chat session
                if not response.chat_session:
                    chat_session = await ChatService.create_session(response_id, db)
                    response.chat_session = chat_session
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

                    await websocket.send_json({
                        "type": "bot_message",
                        "message": question_text,
                        "question_index": current_question_index,
                        "total_questions": len(interview_questions),
                        "progress": f"Вопрос {current_question_index + 1} из {len(interview_questions)}"
                    })
                else:
                    # No questions generated
                    await websocket.send_json({
                        "type": "chat_ended",
                        "message": interview_result.get("closing_message", "Интервью завершено"),
                        "completed": True
                    })
                    return

            # Listen for candidate messages
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                candidate_message = message_data.get("message", "")

                if not candidate_message:
                    continue

                # Create or get chat session (in case it wasn't created earlier)
                if not response.chat_session:
                    chat_session = await ChatService.create_session(response_id, db)
                    response.chat_session = chat_session

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

