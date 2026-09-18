import { Router, type IRouter } from "express";
import healthRouter from "./health";
import inspectionRouter from "./inspection";
import candidateListingsRouter from "./candidate-listings";

const router: IRouter = Router();

router.use(healthRouter);
router.use(inspectionRouter);
router.use(candidateListingsRouter);

export default router;
