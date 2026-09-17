import { Router, type IRouter } from "express";
import healthRouter from "./health";
import inspectionRouter from "./inspection";

const router: IRouter = Router();

router.use(healthRouter);
router.use(inspectionRouter);

export default router;
